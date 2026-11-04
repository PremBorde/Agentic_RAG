import sqlite3
import json
import os
import uuid
import hashlib
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "agent_studio.db")

def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with row factory enabled."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes tables for users, tasks, long-term memory, and pending sensitive actions."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users (OAuth Multi-user management)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        google_access_token TEXT,
        google_refresh_token TEXT,
        token_expires_at TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # Tasks & Reminders (linked to user_id)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id),
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        due_date TEXT,
        priority TEXT DEFAULT 'medium',
        status TEXT DEFAULT 'pending',
        category TEXT DEFAULT 'general',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # Migration: check if user_id column exists on existing tasks table
    cursor.execute("PRAGMA table_info(tasks)")
    columns = [row[1] for row in cursor.fetchall()]
    if "user_id" not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN user_id TEXT REFERENCES users(id)")

    # Migration: check and add missing columns to users
    cursor.execute("PRAGMA table_info(users)")
    u_cols = [row[1] for row in cursor.fetchall()]
    if "display_name" not in u_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
    if "password_hash" not in u_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if "updated_at" not in u_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN updated_at TEXT")

    # Migration: check and add missing columns to conversations
    cursor.execute("PRAGMA table_info(conversations)")
    c_cols = [row[1] for row in cursor.fetchall()]
    if "last_message_at" not in c_cols:
        cursor.execute("ALTER TABLE conversations ADD COLUMN last_message_at TEXT")
    if "archived_at" not in c_cols:
        cursor.execute("ALTER TABLE conversations ADD COLUMN archived_at TEXT")

    # Migration: check and add missing columns to messages
    cursor.execute("PRAGMA table_info(messages)")
    m_cols = [row[1] for row in cursor.fetchall()]
    if "user_id" not in m_cols:
        cursor.execute("ALTER TABLE messages ADD COLUMN user_id TEXT")
    if "message_type" not in m_cols:
        cursor.execute("ALTER TABLE messages ADD COLUMN message_type TEXT DEFAULT 'text'")

    # Normalized indexes for performance & isolation
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(user_id, updated_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv_created ON messages(conversation_id, created_at ASC)")

    # Long-Term Memories & User Preferences
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        category TEXT DEFAULT 'preference',
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # Pending Sensitive Actions (Human-in-the-Loop approval)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pending_actions (
        id TEXT PRIMARY KEY,
        action_type TEXT NOT NULL,
        summary TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TEXT NOT NULL,
        executed_at TEXT
    )
    """)

    # Conversations (Chat Threads)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        title TEXT NOT NULL,
        model TEXT NOT NULL DEFAULT 'gemini-3.5-flash-lite',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # Messages (Thread turns & metadata)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        sender TEXT NOT NULL,
        text TEXT NOT NULL,
        source TEXT,
        metadata_json TEXT DEFAULT '{}',
        created_at TEXT NOT NULL,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id)")

    conn.commit()
    conn.close()

# Initialize DB on import
init_db()

# ─────────────────────────────────────────────────────────────────────────────
# User CRUD (OAuth Multi-user management)
# ─────────────────────────────────────────────────────────────────────────────

def create_or_update_user(
    email: str,
    google_access_token: Optional[str] = None,
    google_refresh_token: Optional[str] = None,
    token_expires_at: Optional[str] = None
) -> Dict[str, Any]:
    """Creates a new user or updates their OAuth credentials if they already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, google_refresh_token FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    now = datetime.utcnow().isoformat()

    if row:
        user_id = row["id"]
        refresh_tok = google_refresh_token if google_refresh_token else row["google_refresh_token"]
        cursor.execute("""
            UPDATE users
            SET google_access_token = ?,
                google_refresh_token = ?,
                token_expires_at = ?
            WHERE id = ?
        """, (google_access_token, refresh_tok, token_expires_at, user_id))
    else:
        user_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO users (id, email, google_access_token, google_refresh_token, token_expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, email, google_access_token, google_refresh_token, token_expires_at, now))

    conn.commit()
    conn.close()
    return get_user_by_id(user_id)

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a user profile by ID."""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_email_raw(email: str) -> Optional[Dict[str, Any]]:
    """Retrieves a user profile by Email."""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None

get_user_by_email = get_user_by_email_raw

def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a unique random salt."""
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return f"pbkdf2_sha256$100000${salt}${derived}"

def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored PBKDF2 hash using constant-time comparison."""
    if not hashed_password or not hashed_password.startswith("pbkdf2_sha256$"):
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4:
            return False
        _, iterations_str, salt, stored_hash = parts
        iterations = int(iterations_str)
        computed_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations).hex()
        return secrets.compare_digest(computed_hash, stored_hash)
    except Exception:
        return False

def sanitize_user_dict(user: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Removes sensitive credentials before returning user dictionary to API callers."""
    if not user:
        return None
    d = dict(user)
    d.pop("password_hash", None)
    d.pop("google_access_token", None)
    d.pop("google_refresh_token", None)
    d["has_google_connected"] = bool(user.get("google_refresh_token") or user.get("google_access_token"))
    return d

def register_user(email: str, password: str, display_name: Optional[str] = None) -> Dict[str, Any]:
    """Registers a new user with password authentication."""
    clean_email = email.strip().lower()
    if not clean_email or "@" not in clean_email or "." not in clean_email:
        raise ValueError("A valid email address is required.")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash FROM users WHERE email = ?", (clean_email,))
    existing = cursor.fetchone()

    now = datetime.utcnow().isoformat()
    hashed = hash_password(password)
    clean_name = display_name.strip() if display_name else clean_email.split("@")[0].title()

    if existing:
        if existing["password_hash"]:
            conn.close()
            raise ValueError("An account with this email already exists. Please log in.")
        user_id = existing["id"]
        cursor.execute("""
            UPDATE users
            SET password_hash = ?, display_name = COALESCE(display_name, ?), updated_at = ?
            WHERE id = ?
        """, (hashed, clean_name, now, user_id))
    else:
        user_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO users (id, email, password_hash, display_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, clean_email, hashed, clean_name, now, now))

    conn.commit()
    conn.close()

    user = get_user_by_id(user_id)
    return sanitize_user_dict(user)

def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates user credentials and returns sanitized profile if valid."""
    clean_email = email.strip().lower()
    user = get_user_by_email_raw(clean_email)
    if not user or not user.get("password_hash"):
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    conn = get_db_connection()
    conn.execute("UPDATE users SET updated_at = ? WHERE id = ?", (datetime.utcnow().isoformat(), user["id"]))
    conn.commit()
    conn.close()

    return sanitize_user_dict(user)


# ─────────────────────────────────────────────────────────────────────────────
# Task & Reminder CRUD
# ─────────────────────────────────────────────────────────────────────────────

def create_task(
    title: str,
    description: str = "",
    due_date: Optional[str] = None,
    priority: str = "medium",
    category: str = "general",
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    task_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO tasks (id, user_id, title, description, due_date, priority, status, category, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
        """,
        (task_id, user_id, title.strip(), description.strip(), due_date, priority.lower(), category.lower(), now, now)
    )
    conn.commit()
    conn.close()
    return get_task(task_id)

def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def list_tasks(
    status: Optional[str] = None,
    category: Optional[str] = None,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if user_id:
        query += " AND (user_id = ? OR user_id IS NULL)"
        params.append(user_id)
    if status:
        query += " AND status = ?"
        params.append(status.lower())
    if category:
        query += " AND category = ?"
        params.append(category.lower())
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, tuple(params)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_task(
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    task = get_task(task_id)
    if not task:
        return None
    
    now = datetime.utcnow().isoformat()
    new_title = title if title is not None else task["title"]
    new_desc = description if description is not None else task["description"]
    new_due = due_date if due_date is not None else task["due_date"]
    new_priority = priority.lower() if priority is not None else task["priority"]
    new_status = status.lower() if status is not None else task["status"]
    new_cat = category.lower() if category is not None else task["category"]

    conn = get_db_connection()
    conn.execute(
        """
        UPDATE tasks
        SET title = ?, description = ?, due_date = ?, priority = ?, status = ?, category = ?, updated_at = ?
        WHERE id = ?
        """,
        (new_title, new_desc, new_due, new_priority, new_status, new_cat, now, task_id)
    )
    conn.commit()
    conn.close()
    return get_task(task_id)

def complete_task(task_id: str) -> Optional[Dict[str, Any]]:
    return update_task(task_id, status="completed")

def delete_task(task_id: str) -> bool:
    conn = get_db_connection()
    cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted

def get_overdue_tasks() -> List[Dict[str, Any]]:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT * FROM tasks
        WHERE status != 'completed' AND due_date IS NOT NULL AND due_date < ?
        ORDER BY due_date ASC
        """,
        (today,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─────────────────────────────────────────────────────────────────────────────
# Long-Term Memory CRUD
# ─────────────────────────────────────────────────────────────────────────────

def add_memory(content: str, category: str = "preference") -> Dict[str, Any]:
    mem_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO memories (id, category, content, created_at) VALUES (?, ?, ?, ?)",
        (mem_id, category.lower(), content.strip(), now)
    )
    conn.commit()
    conn.close()
    return {"id": mem_id, "category": category, "content": content, "created_at": now}

def list_memories(category: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if category:
        rows = conn.execute("SELECT * FROM memories WHERE category = ? ORDER BY created_at DESC", (category.lower(),)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM memories ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_memory(memory_id: str) -> bool:
    conn = get_db_connection()
    cur = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted

def get_relevant_memories_text() -> str:
    """Returns a consolidated summary of persistent user preferences for agent prompts."""
    memories = list_memories()
    if not memories:
        return "No persistent user memories saved."
    lines = [f"- [{m['category'].upper()}] {m['content']}" for m in memories[:15]]
    return "\n".join(lines)

# ─────────────────────────────────────────────────────────────────────────────
# Pending Actions (Human-in-the-Loop Approvals)
# ─────────────────────────────────────────────────────────────────────────────

def create_pending_action(action_type: str, summary: str, payload: Dict[str, Any]) -> str:
    action_id = f"act_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO pending_actions (id, action_type, summary, payload_json, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)",
        (action_id, action_type, summary, json.dumps(payload), now)
    )
    conn.commit()
    conn.close()
    return action_id

def get_pending_action(action_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM pending_actions WHERE id = ?", (action_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["payload"] = json.loads(d["payload_json"])
    return d

def update_action_status(action_id: str, status: str) -> bool:
    now = datetime.utcnow().isoformat()
    conn = get_db_connection()
    cur = conn.execute(
        "UPDATE pending_actions SET status = ?, executed_at = ? WHERE id = ?",
        (status, now, action_id)
    )
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated

# ─────────────────────────────────────────────────────────────────────────────
# Conversations & Messages Persistence
# ─────────────────────────────────────────────────────────────────────────────

def create_or_update_conversation(
    thread_id: str,
    title: str,
    model: str = "gemini-3.5-flash-lite",
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM conversations WHERE id = ?", (thread_id,))
    existing = cursor.fetchone()
    if existing:
        cursor.execute(
            "UPDATE conversations SET title = ?, model = ?, updated_at = ? WHERE id = ?",
            (title, model, now, thread_id)
        )
    else:
        cursor.execute(
            "INSERT INTO conversations (id, user_id, title, model, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (thread_id, user_id, title, model, now, now)
        )
    conn.commit()
    conn.close()
    return {"id": thread_id, "user_id": user_id, "title": title, "model": model, "updated_at": now}

def list_conversations(user_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if user_id:
        rows = conn.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_conversation_with_messages(thread_id: str, message_limit: int = 100, message_offset: int = 0) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    c_row = conn.execute("SELECT * FROM conversations WHERE id = ?", (thread_id,)).fetchone()
    if not c_row:
        conn.close()
        return None
    conv = dict(c_row)
    m_rows = conn.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ? OFFSET ?",
        (thread_id, message_limit, message_offset)
    ).fetchall()
    conn.close()
    
    msgs = []
    for r in m_rows:
        m = dict(r)
        meta = json.loads(m.get("metadata_json") or "{}")
        item = {
            "id": m["id"],
            "sender": m["sender"],
            "text": m["text"],
            "source": m.get("source"),
            "timestamp": m["created_at"],
            **meta
        }
        msgs.append(item)
    conv["messages"] = msgs
    return conv

def save_conversation_message(
    thread_id: str,
    msg_id: str,
    sender: str,
    text: str,
    source: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    created_at: Optional[str] = None,
    user_id: Optional[str] = None,
    message_type: str = "text"
) -> Dict[str, Any]:
    now = created_at or datetime.utcnow().isoformat()
    meta_json = json.dumps(metadata or {})
    conn = get_db_connection()
    # Ensure conversation exists with proper user_id binding
    conn.execute(
        """INSERT INTO conversations (id, user_id, title, model, created_at, updated_at, last_message_at)
           VALUES (?, ?, ?, 'gemini-3.5-flash-lite', ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
             updated_at = excluded.updated_at,
             last_message_at = excluded.last_message_at,
             user_id = COALESCE(conversations.user_id, excluded.user_id)""",
        (thread_id, user_id, text[:40].strip() or "New Conversation", now, now, now)
    )
    # Insert or update message with user_id and message_type
    conn.execute(
        """INSERT INTO messages (id, conversation_id, user_id, sender, text, source, message_type, metadata_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
             text = excluded.text,
             source = excluded.source,
             message_type = excluded.message_type,
             metadata_json = excluded.metadata_json""",
        (msg_id, thread_id, user_id, sender, text, source, message_type, meta_json, now)
    )
    # Update conversation's updated_at and last_message_at
    conn.execute("UPDATE conversations SET updated_at = ?, last_message_at = ? WHERE id = ?", (now, now, thread_id))
    conn.commit()
    conn.close()
    return {"id": msg_id, "conversation_id": thread_id, "sender": sender, "text": text}

def save_conversation_thread_batch(
    thread_id: str,
    title: str,
    model: str,
    messages: List[Dict[str, Any]],
    user_id: Optional[str] = None
) -> bool:
    now = datetime.utcnow().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM conversations WHERE id = ?", (thread_id,))
    if cursor.fetchone():
        cursor.execute(
            "UPDATE conversations SET title = ?, model = ?, updated_at = ? WHERE id = ?",
            (title, model, now, thread_id)
        )
    else:
        cursor.execute(
            "INSERT INTO conversations (id, user_id, title, model, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (thread_id, user_id, title, model, now, now)
        )
    for m in messages:
        msg_id = m.get("id") or f"msg_{uuid.uuid4().hex[:10]}"
        sender = m.get("sender", "user")
        text = m.get("text", "")
        source = m.get("source")
        timestamp = m.get("timestamp") or now
        # extract extra fields for metadata_json
        meta = {k: v for k, v in m.items() if k not in ("id", "sender", "text", "source", "timestamp")}
        cursor.execute(
            """INSERT INTO messages (id, conversation_id, sender, text, source, metadata_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 text = excluded.text,
                 source = excluded.source,
                 metadata_json = excluded.metadata_json""",
            (msg_id, thread_id, sender, text, source, json.dumps(meta), timestamp)
        )
    conn.commit()
    conn.close()
    return True

def delete_conversation_thread(thread_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (thread_id,))
    cursor.execute("DELETE FROM conversations WHERE id = ?", (thread_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted



def get_recent_messages_for_context(thread_id: str, limit: int = 12) -> List[Dict[str, Any]]:
    """Retrieves recent thread turns from SQLite to restore context across backend restarts."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT sender, text, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?",
        (thread_id, limit)
    ).fetchall()
    conn.close()
    turns = []
    for r in reversed(rows):
        role = "user" if r["sender"].lower() == "user" else "assistant"
        turns.append({"role": role, "content": r["text"], "timestamp": r["created_at"]})
    return turns

def get_conversation_owner(thread_id: str) -> Optional[str]:
    """Returns the user_id associated with a conversation thread."""
    conn = get_db_connection()
    row = conn.execute("SELECT user_id FROM conversations WHERE id = ?", (thread_id,)).fetchone()
    conn.close()
    return row["user_id"] if row else None

