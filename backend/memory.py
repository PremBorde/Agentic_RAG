from typing import Optional
from datetime import datetime

# Session / Thread Context Memory
thread_histories: dict[str, list[dict]] = {}

def get_thread_context_str(thread_id: Optional[str], max_turns: int = 6) -> str:
    if not thread_id or thread_id not in thread_histories:
        return "No prior conversational context."
    history = thread_histories[thread_id][-max_turns:]
    lines = []
    for h in history:
        speaker = "User" if h.get("role") == "user" else "Assistant"
        lines.append(f"{speaker}: {h.get('content', '')}")
    return "\n".join(lines) if lines else "No prior conversational context."

def record_thread_turn(thread_id: Optional[str], role: str, content: str):
    if not thread_id:
        return
    if thread_id not in thread_histories:
        thread_histories[thread_id] = []
    thread_histories[thread_id].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })

def get_last_user_query(thread_id: Optional[str]) -> str:
    """Returns the most recent user question prior to the current turn from thread history."""
    if not thread_id or thread_id not in thread_histories:
        return ""
    for turn in reversed(thread_histories[thread_id]):
        if turn.get("role") == "user":
            c = turn.get("content", "").strip()
            if c:
                return c
    return ""

