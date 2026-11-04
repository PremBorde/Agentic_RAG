import unittest
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs
from fastapi.testclient import TestClient

from server import app
from backend.routes.auth import (
    sanitize_thread_id,
    sanitize_return_to_path,
    build_redirect_url,
    store_oauth_state,
    pop_oauth_state,
    _oauth_state_cache
)
from backend.services.database import (
    create_or_update_conversation,
    save_conversation_thread_batch,
    get_conversation_with_messages,
    list_conversations,
    delete_conversation_thread
)

client = TestClient(app, follow_redirects=False)

class TestOAuthConversationRedirect(unittest.TestCase):
    def setUp(self):
        _oauth_state_cache.clear()

    def test_01_oauth_from_conversation_restores_same_thread(self):
        """Test that initiating OAuth from an active thread returns to that thread upon success."""
        test_thread = "thread_1793773"

        # 1. Initiate OAuth login with thread_id
        with patch("backend.routes.auth.get_oauth_url") as mock_get_url:
            mock_get_url.return_value = {
                "url": "https://accounts.google.com/o/oauth2/auth?client_id=xyz&state=mock_state_123",
                "state": "mock_state_123",
                "code_verifier": "mock_verifier_123"
            }
            resp = client.get(f"/api/auth/google/login?thread_id={test_thread}&return_to=/?thread_id={test_thread}")
            self.assertEqual(resp.status_code, 307)
            self.assertIn("mock_state_123", resp.headers["location"])

        # State should be securely recorded
        self.assertIn("mock_state_123", _oauth_state_cache)
        self.assertEqual(_oauth_state_cache["mock_state_123"]["thread_id"], test_thread)

        # 2. Simulate successful Google OAuth callback
        with patch("backend.routes.auth.exchange_code_for_user") as mock_exchange:
            mock_exchange.return_value = {
                "success": True,
                "user_id": "test_user_1",
                "email": "test@gmail.com"
            }
            cb_resp = client.get("/api/auth/google/callback?code=mock_code&state=mock_state_123")
            self.assertEqual(cb_resp.status_code, 307)
            loc = cb_resp.headers["location"]
            parsed = urlparse(loc)
            qs = parse_qs(parsed.query)
            
            # Assert target URL restores the original thread
            self.assertEqual(qs.get("connected"), ["true"])
            self.assertEqual(qs.get("thread_id"), [test_thread])
            # Ensure no tokens leaked
            self.assertNotIn("token", qs)
            self.assertNotIn("code", qs)

    def test_02_oauth_from_home_page_returns_to_home(self):
        """Test that initiating OAuth from home page without a thread returns to home."""
        with patch("backend.routes.auth.get_oauth_url") as mock_get_url:
            mock_get_url.return_value = {
                "url": "https://accounts.google.com/o/oauth2/auth?client_id=xyz&state=mock_state_home",
                "state": "mock_state_home",
                "code_verifier": "mock_verifier_home"
            }
            resp = client.get("/api/auth/google/login?return_to=/")
            self.assertEqual(resp.status_code, 307)

        with patch("backend.routes.auth.exchange_code_for_user") as mock_exchange:
            mock_exchange.return_value = {
                "success": True,
                "user_id": "test_user_home",
                "email": "home@gmail.com"
            }
            cb_resp = client.get("/api/auth/google/callback?code=mock_code&state=mock_state_home")
            self.assertEqual(cb_resp.status_code, 307)
            loc = cb_resp.headers["location"]
            parsed = urlparse(loc)
            qs = parse_qs(parsed.query)

            self.assertEqual(qs.get("connected"), ["true"])
            self.assertNotIn("thread_id", qs)
            self.assertEqual(parsed.path, "/")

    def test_03_oauth_failure_or_cancellation_restores_thread_with_error(self):
        """Test that OAuth cancellation or Google error redirects back to original thread with error param."""
        test_thread = "thread_cancel_999"
        store_oauth_state(
            state="state_cancelled",
            code_verifier="cv_cancel",
            thread_id=test_thread,
            return_to=f"/?thread_id={test_thread}"
        )

        # Google calls callback with error=access_denied
        cb_resp = client.get("/api/auth/google/callback?error=access_denied&error_description=User+denied+access&state=state_cancelled")
        self.assertEqual(cb_resp.status_code, 307)
        loc = cb_resp.headers["location"]
        parsed = urlparse(loc)
        qs = parse_qs(parsed.query)

        self.assertEqual(qs.get("thread_id"), [test_thread])
        self.assertIn("oauth_error", qs)
        self.assertNotIn("connected", qs)

    def test_04_concurrent_tabs_preserve_separate_thread_ids(self):
        """Test that multiple browser tabs initiating OAuth concurrently do not overwrite each other."""
        tab1_thread = "thread_tab_alpha"
        tab2_thread = "thread_tab_beta"

        # Tab 1 starts OAuth
        store_oauth_state("state_tab_1", "cv_1", tab1_thread, f"/?thread_id={tab1_thread}")
        # Tab 2 starts OAuth concurrently
        store_oauth_state("state_tab_2", "cv_2", tab2_thread, f"/?thread_id={tab2_thread}")

        # Both states must exist simultaneously in cache
        self.assertIn("state_tab_1", _oauth_state_cache)
        self.assertIn("state_tab_2", _oauth_state_cache)

        with patch("backend.routes.auth.exchange_code_for_user") as mock_exchange:
            mock_exchange.return_value = {"success": True, "user_id": "u1", "email": "u1@gmail.com"}
            
            # Tab 2 finishes OAuth first
            cb_resp2 = client.get("/api/auth/google/callback?code=c2&state=state_tab_2")
            parsed2 = urlparse(cb_resp2.headers["location"])
            qs2 = parse_qs(parsed2.query)
            self.assertEqual(qs2.get("thread_id"), [tab2_thread])

            # Tab 1 finishes OAuth second
            cb_resp1 = client.get("/api/auth/google/callback?code=c1&state=state_tab_1")
            parsed1 = urlparse(cb_resp1.headers["location"])
            qs1 = parse_qs(parsed1.query)
            self.assertEqual(qs1.get("thread_id"), [tab1_thread])

    def test_05_existing_conversation_messages_remain_intact_and_no_duplicate(self):
        """Test that existing conversation messages remain unchanged and no duplicate thread is created."""
        user_id = "test_persistence_user"
        test_thread = "thread_persist_123"
        initial_messages = [
            {"id": "1", "sender": "user", "text": "Who is Alan Turing?", "timestamp": "12:00 PM"},
            {"id": "2", "sender": "assistant", "text": "Alan Turing was a mathematician.", "timestamp": "12:01 PM"}
        ]
        
        # Save initial conversation in database
        save_conversation_thread_batch(test_thread, "Turing Discussion", "gemini-2.5-flash", initial_messages, user_id)
        
        count_before = len(list_conversations(user_id))

        # Initiate OAuth from this conversation
        store_oauth_state("state_persist", "cv_p", test_thread, f"/?thread_id={test_thread}")

        # Complete OAuth callback
        with patch("backend.routes.auth.exchange_code_for_user") as mock_exchange:
            mock_exchange.return_value = {"success": True, "user_id": user_id, "email": "user@gmail.com"}
            cb_resp = client.get("/api/auth/google/callback?code=cp&state=state_persist")
            self.assertEqual(cb_resp.status_code, 307)
            self.assertIn(f"thread_id={test_thread}", cb_resp.headers["location"])

        # Verify conversation in database is identical
        thread_data = get_conversation_with_messages(test_thread)
        self.assertIsNotNone(thread_data)
        self.assertEqual(len(thread_data["messages"]), 2)
        self.assertEqual(thread_data["messages"][0]["text"], "Who is Alan Turing?")
        self.assertEqual(thread_data["messages"][1]["text"], "Alan Turing was a mathematician.")

        # Verify no duplicate conversation thread was created
        count_after = len(list_conversations(user_id))
        self.assertEqual(count_after, count_before)

        # Cleanup
        delete_conversation_thread(test_thread)

    def test_06_open_redirect_protection(self):
        """Test that malicious external return URLs are sanitized to prevent open redirects."""
        malicious_urls = [
            "https://attacker.com",
            "http://evil.com/phish",
            "//attacker.com/evil",
            "/\\evil.com",
            "javascript:alert(1)"
        ]
        for bad_url in malicious_urls:
            sanitized = sanitize_return_to_path(bad_url)
            self.assertIsNone(sanitized, f"Failed to reject malicious URL: {bad_url}")

            redirect_url = build_redirect_url(base_return=bad_url, thread_id="thread_safe_1")
            parsed = urlparse(redirect_url)
            self.assertEqual(parsed.netloc, "", f"Open redirect detected: {redirect_url}")
            self.assertTrue(redirect_url.startswith("/?"), f"Unsafe redirect URL: {redirect_url}")

if __name__ == "__main__":
    unittest.main()
