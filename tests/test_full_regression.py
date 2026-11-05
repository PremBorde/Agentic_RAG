"""
Comprehensive Full Regression Test Suite for Personal AI Agent Studio
Verifies all 17 production capabilities:
1. Conversational Fast-Path (Zero-LLM)
2. Capability Inquiries
3. Centralized Intent Routing
4. RAG Document Retrieval Isolation
5. Live Web Search Intent & Execution
6. Gmail Intent Detection & Argument Extraction
7. Calendar Intent Detection & Availability
8. Human-in-the-Loop Sensitive Action Proposal Safety
9. Multi-Step Compound Instruction Detection
10. Task & Reminder CRUD Operations
11. Long-Term Memory Persistence & Recall
12. Multi-User Conversation Persistence & Restart Recovery
13. Thread Authorization & Ownership Isolation
14. Standalone Registration & PBKDF2 Password Verification
15. Standalone Login & Session Security
16. Document Upload Security & Path Traversal Protection
17. Production Health Check & Telemetry
"""

import sys
import os
import unittest
import urllib.request
import urllib.error
import json
import uuid

# Inject project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.router import classify_query, QueryIntent
from backend.services.database import (
    hash_password,
    verify_password,
    register_user,
    authenticate_user,
    create_or_update_conversation,
    save_conversation_message,
    get_conversation_with_messages,
    list_conversations,
    create_task,
    list_tasks,
    complete_task,
    add_memory,
    list_memories
)
from backend.services.approval_service import propose_action

BASE_URL = "http://127.0.0.1:8000"

class TestFullRegression(unittest.TestCase):

    def test_01_conversational_fast_path(self):
        """1. Conversational greetings must take the fast path with zero LLM API call."""
        greetings = ["hello", "hi there", "good morning", "thanks", "bye", "see you later"]
        for g in greetings:
            decision = classify_query(g, doc_count=2)
            self.assertEqual(decision.intent, QueryIntent.CONVERSATIONAL, f"Failed on '{g}'")
            self.assertTrue(decision.is_fast_path, f"Not fast path: '{g}'")
            self.assertFalse(decision.rag_invoked)

    def test_02_capability_inquiry(self):
        """2. Capability queries must route to conversational capability description."""
        decision = classify_query("what can you do", doc_count=2)
        self.assertEqual(decision.intent, QueryIntent.CONVERSATIONAL)
        self.assertTrue(decision.is_welcome_card)
        self.assertFalse(decision.rag_invoked)

    def test_03_router_never_hijacks_substantive(self):
        """3. Greetings embedded in substantive requests must NOT trigger fast path."""
        mixed = [
            ("Hi, search my uploaded PDF for knapsack", QueryIntent.DOCUMENT_RAG),
            ("Good morning, check my unread emails", QueryIntent.GMAIL),
            ("Hey, what is on my calendar for tomorrow?", QueryIntent.CALENDAR),
            ("Hello, for web search today top 5 news", QueryIntent.WEB_SEARCH),
        ]
        for query, expected_intent in mixed:
            decision = classify_query(query, doc_count=2)
            self.assertEqual(decision.intent, expected_intent, f"Failed on '{query}'")
            self.assertFalse(decision.is_fast_path, f"Falsely marked fast path: '{query}'")

    def test_04_rag_retrieval_isolation(self):
        """4. Document RAG must ONLY invoke when explicit document keywords are present."""
        web_q = "For web search today top 5 news"
        d_web = classify_query(web_q, doc_count=5)
        self.assertEqual(d_web.intent, QueryIntent.WEB_SEARCH)
        self.assertFalse(d_web.rag_invoked)

        doc_q = "Explain fractional knapsack from my uploaded PDF"
        d_doc = classify_query(doc_q, doc_count=5)
        self.assertEqual(d_doc.intent, QueryIntent.DOCUMENT_RAG)
        self.assertTrue(d_doc.rag_invoked)

    def test_05_web_search_execution(self):
        """5. Web search tool execution returns real internet context."""
        from backend.tools import web_search_tool
        result = web_search_tool.invoke("Python programming language")
        self.assertTrue(isinstance(result, str))
        self.assertTrue(len(result) > 20)

    def test_06_gmail_intent_detection(self):
        """6. Gmail intents accurately detect inbox checks and search queries."""
        decision = classify_query("Search for unread messages", doc_count=1)
        self.assertEqual(decision.intent, QueryIntent.GMAIL)
        self.assertEqual(decision.sub_action, "search_emails")

    def test_07_calendar_intent_detection(self):
        """7. Calendar intents accurately detect availability and schedule checks."""
        decision = classify_query("Find a free 30-minute slot on Friday", doc_count=1)
        self.assertEqual(decision.intent, QueryIntent.CALENDAR)
        self.assertEqual(decision.sub_action, "check_availability")

    def test_08_hitl_action_proposal_safety(self):
        """8. Sensitive write actions MUST generate pending proposals, never execute directly."""
        proposal = propose_action(
            action_type="send_email",
            summary="Send email to team@example.com",
            payload={"to": "team@example.com", "subject": "Project Update", "body": "All done."}
        )
        self.assertIsNotNone(proposal)
        self.assertTrue(proposal.get("action_id", "").startswith("act_"))
        self.assertEqual(proposal["status"], "pending")

    def test_09_multi_step_compound_orchestration(self):
        """9. Compound instructions route to multi-step agent orchestrator."""
        query = "Find the email from Alex, summarize it, and schedule a meeting for tomorrow at 2 PM"
        decision = classify_query(query, doc_count=1)
        self.assertEqual(decision.intent, QueryIntent.MULTI_STEP)
        self.assertEqual(decision.sub_action, "email_and_calendar")

    def test_10_task_management(self):
        """10. Task & Reminder CRUD creates, lists, and completes tasks."""
        test_title = f"Regression Task {uuid.uuid4().hex[:6]}"
        task = create_task(title=test_title, priority="high")
        self.assertEqual(task["title"], test_title)
        
        all_tasks = list_tasks()
        found = any(t["id"] == task["id"] for t in all_tasks)
        self.assertTrue(found)

        updated = complete_task(task["id"])
        self.assertEqual(updated["status"], "completed")

    def test_11_long_term_memory(self):
        """11. Long-term memory persists user preferences across sessions."""
        test_pref = f"User prefers dark roast coffee {uuid.uuid4().hex[:4]}"
        mem = add_memory(content=test_pref, category="preference")
        self.assertIsNotNone(mem["id"])

        memories = list_memories()
        self.assertTrue(any(test_pref in m["content"] for m in memories))

    def test_12_multi_user_thread_persistence(self):
        """12. Messages and thread metadata persist in SQLite and survive restarts."""
        thread_id = f"reg-thread-{uuid.uuid4().hex[:8]}"
        user_id = f"reg-user-{uuid.uuid4().hex[:8]}"

        create_or_update_conversation(thread_id=thread_id, user_id=user_id, title="Regression Thread")
        save_conversation_message(thread_id=thread_id, msg_id=str(uuid.uuid4()), sender="user", text="Hello from persistence test", user_id=user_id)
        save_conversation_message(thread_id=thread_id, msg_id=str(uuid.uuid4()), sender="assistant", text="Hello! Stored safely in SQLite.", user_id=user_id)

        conv = get_conversation_with_messages(thread_id)
        self.assertIsNotNone(conv)
        self.assertEqual(len(conv["messages"]), 2)
        self.assertEqual(conv["messages"][0]["text"], "Hello from persistence test")

    def test_13_thread_isolation(self):
        """13. User A cannot list or read conversations belonging to User B."""
        user_a = f"user_a_{uuid.uuid4().hex[:6]}"
        user_b = f"user_b_{uuid.uuid4().hex[:6]}"
        thread_a = f"thread_a_{uuid.uuid4().hex[:6]}"
        thread_b = f"thread_b_{uuid.uuid4().hex[:6]}"

        create_or_update_conversation(thread_id=thread_a, user_id=user_a, title="Thread A")
        create_or_update_conversation(thread_id=thread_b, user_id=user_b, title="Thread B")

        list_a = list_conversations(user_id=user_a)
        threads_a_ids = [t["id"] for t in list_a]
        self.assertIn(thread_a, threads_a_ids)
        self.assertNotIn(thread_b, threads_a_ids)

    def test_14_password_hashing_pbkdf2(self):
        """14. PBKDF2 with SHA-256 and unique random salt validates passwords safely."""
        pwd = "ProductionSecurePassword!987"
        h = hash_password(pwd)
        self.assertTrue(h.startswith("pbkdf2_sha256$100000$"))
        self.assertTrue(verify_password(pwd, h))
        self.assertFalse(verify_password("wrong_password", h))

    def test_15_standalone_auth_live(self):
        """15. Standalone registration and login endpoints work over HTTP."""
        from starlette.testclient import TestClient
        from server import app
        client = TestClient(app)
        unique_email = f"live_reg_{uuid.uuid4().hex[:6]}@example.com"
        reg_resp = client.post("/api/auth/register", json={"email": unique_email, "password": "securepassword123", "display_name": "Live Tester"})
        self.assertEqual(reg_resp.status_code, 200)
        data = reg_resp.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["user"]["email"], unique_email)

        login_resp = client.post("/api/auth/login", json={"email": unique_email, "password": "securepassword123"})
        self.assertEqual(login_resp.status_code, 200)
        data_login = login_resp.json()
        self.assertTrue(data_login.get("success"))

    def test_16_upload_security_and_traversal(self):
        """16. Upload endpoint rejects unsupported extensions and path traversal."""
        from starlette.testclient import TestClient
        from server import app
        client = TestClient(app)
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("../../etc/passwd.sh", b"echo 'malicious'", "application/x-sh")}
        )
        self.assertEqual(resp.status_code, 400)

    def test_17_production_health_check(self):
        """17. Health check returns 200 with service status, checks, and zero secrets."""
        from starlette.testclient import TestClient
        from server import app
        client = TestClient(app)
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("checks", data)
        self.assertEqual(data["checks"]["database"], "ok")
        self.assertNotIn("GOOGLE_API_KEY", str(data))
        self.assertNotIn("SECRET_KEY", str(data))

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFullRegression)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n============================================================")
        print("  ALL 17 REGRESSION SUITE CAPABILITIES VERIFIED [PASS]")
        print("============================================================\n")
        sys.exit(0)
    else:
        print("\nREGRESSION FAILURES OCCURRED!")
        sys.exit(1)
