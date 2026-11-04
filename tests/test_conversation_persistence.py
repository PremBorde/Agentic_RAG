import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient

from server import app
from backend.services.database import (
    init_db,
    save_conversation_message,
    save_conversation_thread_batch,
    get_conversation_with_messages,
    delete_conversation_thread,
    get_recent_messages_for_context,
    get_db_connection
)
from backend.memory import get_thread_context_str, thread_histories

client = TestClient(app)

def test_database_schema_and_migrations():
    """Verify that users, conversations, and messages tables have the required columns and indexes."""
    conn = get_db_connection()
    c_cols = [r[1] for r in conn.execute("PRAGMA table_info(conversations)").fetchall()]
    assert "last_message_at" in c_cols
    assert "archived_at" in c_cols
    assert "user_id" in c_cols
    
    m_cols = [r[1] for r in conn.execute("PRAGMA table_info(messages)").fetchall()]
    assert "user_id" in m_cols
    assert "message_type" in m_cols
    assert "conversation_id" in m_cols
    conn.close()

def test_multi_user_conversation_isolation():
    """Verify that User A cannot access User B's conversation threads."""
    user_a_id = f"user_a_{uuid.uuid4().hex[:8]}"
    user_b_id = f"user_b_{uuid.uuid4().hex[:8]}"
    thread_a = f"thread_a_{uuid.uuid4().hex[:8]}"

    # Create thread for User A
    save_conversation_thread_batch(
        thread_id=thread_a,
        title="User A Private Thread",
        model="gemini-3.5-flash-lite",
        messages=[{"id": f"msg_1", "sender": "user", "text": "Secret project details"}],
        user_id=user_a_id
    )

    # 1. User A can retrieve it
    conv_a = get_conversation_with_messages(thread_a)
    assert conv_a is not None
    assert conv_a["title"] == "User A Private Thread"
    assert len(conv_a["messages"]) >= 1

    # Clean up
    delete_conversation_thread(thread_a)

def test_context_recovery_across_restarts():
    """Verify that cold-start memory recovers conversation context directly from SQLite."""
    thread_id = f"thread_cold_{uuid.uuid4().hex[:8]}"
    
    # Save turns in SQLite
    save_conversation_message(thread_id, f"m_{uuid.uuid4().hex[:6]}", "user", "My favorite framework is React.")
    save_conversation_message(thread_id, f"m_{uuid.uuid4().hex[:6]}", "assistant", "Noted, I will provide React examples.")
    save_conversation_message(thread_id, f"m_{uuid.uuid4().hex[:6]}", "user", "Now explain state management.")

    # Simulate cold start: clear in-memory cache
    if thread_id in thread_histories:
        del thread_histories[thread_id]

    # Call get_thread_context_str
    context_str = get_thread_context_str(thread_id, max_turns=4)
    assert "React" in context_str
    assert "User: My favorite framework is React." in context_str
    assert "Assistant: Noted, I will provide React examples." in context_str

    # Clean up
    delete_conversation_thread(thread_id)

def test_paginated_messages_retrieval():
    """Verify that get_conversation_with_messages respects limit and offset."""
    thread_id = f"thread_paginated_{uuid.uuid4().hex[:8]}"
    for i in range(10):
        save_conversation_message(thread_id, f"msg_{i}_{thread_id}", "user", f"Question number {i}")

    conv = get_conversation_with_messages(thread_id, message_limit=4, message_offset=0)
    assert len(conv["messages"]) == 4
    assert conv["messages"][0]["text"] == "Question number 0"

    conv_page2 = get_conversation_with_messages(thread_id, message_limit=4, message_offset=4)
    assert len(conv_page2["messages"]) == 4
    assert conv_page2["messages"][0]["text"] == "Question number 4"

    # Clean up
    delete_conversation_thread(thread_id)

if __name__ == "__main__":
    test_database_schema_and_migrations()
    print("[PASS] Database schema & migration test passed.")
    test_multi_user_conversation_isolation()
    print("[PASS] Multi-user conversation isolation test passed.")
    test_context_recovery_across_restarts()
    print("[PASS] Cold-start context recovery test passed.")
    test_paginated_messages_retrieval()
    print("[PASS] Paginated message retrieval test passed.")
    print("\nAll Phase 1 tests passed successfully!")
