import os
import unittest
import uuid
from backend.services.database import (
    get_db_connection,
    save_conversation_message,
    save_conversation_thread_batch,
    get_conversation_with_messages,
    delete_conversation_thread
)

class TestMessageDeduplicationAndUI(unittest.TestCase):
    def setUp(self):
        self.test_thread = f"test_dedup_{uuid.uuid4().hex[:8]}"

    def tearDown(self):
        delete_conversation_thread(self.test_thread)

    def test_01_single_message_persisted_with_client_id(self):
        """User message is persisted with its client-provided unique ID."""
        u_id = f"msg_user_{uuid.uuid4().hex[:8]}"
        res = save_conversation_message(self.test_thread, u_id, "user", "Who is Sam Altman?")
        self.assertEqual(res["id"], u_id)

        conv = get_conversation_with_messages(self.test_thread)
        self.assertIsNotNone(conv)
        self.assertEqual(len(conv["messages"]), 1)
        self.assertEqual(conv["messages"][0]["id"], u_id)
        self.assertEqual(conv["messages"][0]["text"], "Who is Sam Altman?")

    def test_02_backend_and_frontend_id_alignment_no_duplicates(self):
        """Backend stream save followed by frontend batch sync does not create duplicate rows."""
        u_id = f"msg_user_{uuid.uuid4().hex[:8]}"
        a_id = f"msg_ai_{uuid.uuid4().hex[:8]}"

        # 1. Backend saves during stream
        save_conversation_message(self.test_thread, u_id, "user", "What is AI?")
        save_conversation_message(self.test_thread, a_id, "assistant", "AI is Artificial Intelligence.")

        # Check count = 2
        conv1 = get_conversation_with_messages(self.test_thread)
        self.assertEqual(len(conv1["messages"]), 2)

        # 2. Frontend batch sync arrives with the exact same IDs
        batch_msgs = [
            {"id": u_id, "sender": "user", "text": "What is AI?"},
            {"id": a_id, "sender": "assistant", "text": "AI is Artificial Intelligence."}
        ]
        save_conversation_thread_batch(self.test_thread, "What is AI?", "gemini-2.5-flash", batch_msgs)

        # Check count remains exactly 2 (no duplicate rows inserted)
        conv2 = get_conversation_with_messages(self.test_thread)
        self.assertEqual(len(conv2["messages"]), 2)
        self.assertEqual(conv2["messages"][0]["id"], u_id)
        self.assertEqual(conv2["messages"][1]["id"], a_id)

    def test_03_intentional_repeat_creates_distinct_messages(self):
        """When user intentionally repeats the same query twice, both are preserved with distinct IDs."""
        u_id1 = f"msg_user_1_{uuid.uuid4().hex[:8]}"
        u_id2 = f"msg_user_2_{uuid.uuid4().hex[:8]}"

        save_conversation_message(self.test_thread, u_id1, "user", "Tell me a joke")
        save_conversation_message(self.test_thread, f"msg_ai_1_{uuid.uuid4().hex[:8]}", "assistant", "Joke 1")
        save_conversation_message(self.test_thread, u_id2, "user", "Tell me a joke")
        save_conversation_message(self.test_thread, f"msg_ai_2_{uuid.uuid4().hex[:8]}", "assistant", "Joke 2")

        conv = get_conversation_with_messages(self.test_thread)
        self.assertEqual(len(conv["messages"]), 4)
        user_msgs = [m for m in conv["messages"] if m["sender"] == "user"]
        self.assertEqual(len(user_msgs), 2)
        self.assertEqual(user_msgs[0]["id"], u_id1)
        self.assertEqual(user_msgs[1]["id"], u_id2)

    def test_04_batch_upsert_idempotency_multiple_calls(self):
        """Calling save_conversation_thread_batch multiple times (e.g. on every keystroke or retry) is strictly idempotent."""
        u_id = f"msg_user_{uuid.uuid4().hex[:8]}"
        msgs = [{"id": u_id, "sender": "user", "text": "Hello world"}]

        for _ in range(5):
            save_conversation_thread_batch(self.test_thread, "Hello", "gemini-2.5-flash", msgs)

        conv = get_conversation_with_messages(self.test_thread)
        self.assertEqual(len(conv["messages"]), 1)

    def test_05_metadata_preserved_on_conflict_update(self):
        """Updating message preserves metadata such as citations and source."""
        u_id = f"msg_user_{uuid.uuid4().hex[:8]}"
        a_id = f"msg_ai_{uuid.uuid4().hex[:8]}"

        save_conversation_message(self.test_thread, u_id, "user", "Search DAA")
        save_conversation_message(self.test_thread, a_id, "assistant", "Initial answer", source="RAG")

        # Frontend updates with enriched metadata
        batch_msgs = [
            {"id": u_id, "sender": "user", "text": "Search DAA"},
            {"id": a_id, "sender": "assistant", "text": "Enriched answer", "source": "RAG", "retrievedDocs": [{"title": "DAA.pdf"}]}
        ]
        save_conversation_thread_batch(self.test_thread, "Search DAA", "gemini-2.5-flash", batch_msgs)

        conv = get_conversation_with_messages(self.test_thread)
        self.assertEqual(len(conv["messages"]), 2)
        ai_msg = conv["messages"][1]
        self.assertEqual(ai_msg["text"], "Enriched answer")
        self.assertEqual(ai_msg["source"], "RAG")
        self.assertEqual(ai_msg.get("retrievedDocs"), [{"title": "DAA.pdf"}])

    def test_06_query_request_model_accepts_message_ids(self):
        """QueryRequest pydantic model cleanly accepts optional message_id and assistant_message_id."""
        from backend.routes.chat import QueryRequest
        req = QueryRequest(
            message="Test prompt",
            model="gemini-2.5-flash",
            thread_id="test_th",
            message_id="msg_user_12345",
            assistant_message_id="msg_ai_67890"
        )
        self.assertEqual(req.message_id, "msg_user_12345")
        self.assertEqual(req.assistant_message_id, "msg_ai_67890")

    def test_07_database_thread_deletion_cleans_messages(self):
        """Deleting a thread removes all its messages cleanly without residual orphans."""
        u_id = f"msg_user_{uuid.uuid4().hex[:8]}"
        save_conversation_message(self.test_thread, u_id, "user", "To be deleted")
        delete_conversation_thread(self.test_thread)

        conv = get_conversation_with_messages(self.test_thread)
        self.assertIsNone(conv)

    def test_08_multi_turn_history_order(self):
        """Multi-turn messages maintain correct chronological ordering."""
        turns = [
            ("user", "Hello"),
            ("assistant", "Hi there"),
            ("user", "How are you?"),
            ("assistant", "Doing great!")
        ]
        for role, text in turns:
            save_conversation_message(self.test_thread, f"msg_{role}_{uuid.uuid4().hex[:6]}", role, text)

        conv = get_conversation_with_messages(self.test_thread)
        self.assertEqual(len(conv["messages"]), 4)
        for i, (role, text) in enumerate(turns):
            self.assertEqual(conv["messages"][i]["sender"], role)
            self.assertEqual(conv["messages"][i]["text"], text)

    def test_09_database_dedup_helper_prevents_duplicate_id_in_fetch(self):
        """get_conversation_with_messages returns a unique set of messages even if raw rows had dupes."""
        conn = get_db_connection()
        conn.execute(
            "INSERT OR IGNORE INTO conversations (id, title, model, created_at, updated_at) VALUES (?, 'T', 'M', '2026-01-01', '2026-01-01')",
            (self.test_thread,)
        )
        # Directly insert message
        conn.execute(
            "INSERT OR REPLACE INTO messages (id, conversation_id, sender, text, created_at) VALUES ('fixed_id', ?, 'user', 'msg text', '2026-01-01')",
            (self.test_thread,)
        )
        conn.commit()
        conn.close()

        conv = get_conversation_with_messages(self.test_thread)
        self.assertEqual(len(conv["messages"]), 1)
        self.assertEqual(conv["messages"][0]["id"], "fixed_id")

    def test_10_no_duplicate_groups_in_sqlite(self):
        """Database currently contains zero unintended duplicate groups."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT conversation_id, sender, text, count(*)
            FROM messages
            GROUP BY conversation_id, sender, text
            HAVING count(*) > 1
        """)
        dupes = cursor.fetchall()
        conn.close()
        self.assertEqual(len(dupes), 0, f"Found unexpected duplicate groups in DB: {dupes}")

if __name__ == '__main__':
    unittest.main()

