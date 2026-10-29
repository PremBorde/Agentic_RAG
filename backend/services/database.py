import sqlite3
import json
import os
import uuid
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
    """Initializes tables for tasks, long-term memory, and pending sensitive actions."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tasks & Reminders
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
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

    conn.commit()
    conn.close()

# Initialize DB on import
init_db()

# ─────────────────────────────────────────────────────────────────────────────
# Task & Reminder CRUD
# ─────────────────────────────────────────────────────────────────────────────

def create_task(
    title: str,
    description: str = "",
    due_date: Optional[str] = None,
    priority: str = "medium",
    category: str = "general"
) -> Dict[str, Any]:
    task_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO tasks (id, title, description, due_date, priority, status, category, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)
        """,
        (task_id, title.strip(), description.strip(), due_date, priority.lower(), category.lower(), now, now)
    )
    conn.commit()
    conn.close()
    return get_task(task_id)

def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def list_tasks(status: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
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
