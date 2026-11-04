import re
from typing import Optional, List, Dict
from datetime import datetime

# Session / Thread Context In-Memory Cache
thread_histories: dict[str, list[dict]] = {}

def _ensure_thread_history_loaded(thread_id: str, max_turns: int = 8):
    """Restores recent conversation turns from SQLite into memory cache if not present."""
    if not thread_id:
        return
    if thread_id not in thread_histories or not thread_histories[thread_id]:
        try:
            from backend.services.database import get_recent_messages_for_context
            turns = get_recent_messages_for_context(thread_id, limit=max_turns * 2)
            if turns:
                thread_histories[thread_id] = turns
        except Exception:
            pass

def compress_assistant_turn(content: str, max_chars: int = 350, is_most_recent: bool = False) -> str:
    """
    Deterministic, zero-LLM structured history compressor for assistant responses.
    Preserves:
      - Topic & headings
      - Core answer / definition
      - Numbered options, entities & points (crucial for pronoun resolution e.g. 'the second one')
      - Decisions, recommendations, and conclusions with their original label
    Budgets:
      - Immediate prior assistant turn (t_-1): max(max_chars * 2, 700)
      - Older assistant turns (t < t_-1): max_chars (default 350)
    Runs in < 1ms with 0 Gemini API calls.
    """
    if not content:
        return ""
    cleaned = content.strip()
    effective_limit = max(max_chars * 2, 700) if is_most_recent else max_chars
    if len(cleaned) <= effective_limit:
        return cleaned

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return cleaned[:effective_limit].rstrip() + "..."

    # 1. Topic / Heading
    topic = ""
    first_body = ""
    for line in lines:
        stripped = re.sub(r"^[\*#_\-\s]+", "", line).strip()
        if not topic and (line.startswith("#") or line.startswith("**") or stripped.lower().startswith("topic")):
            topic = stripped
        elif not first_body and len(stripped) > 15:
            first_body = stripped
            if topic:
                break

    # 2. Extract numbered points, options & entities
    items = []
    item_pattern = re.compile(r"^(?:\d+[\.\)]|[-*•])\s+(.+)$")
    for line in lines:
        m = item_pattern.match(line)
        if m:
            item_text = re.sub(r"[\*_]+", "", m.group(1)).strip()
            if len(item_text) > 85:
                item_text = item_text[:82] + "..."
            items.append(item_text)

    # 3. Extract decisions, recommendations, conclusions with preserved label
    decision = ""
    decision_label = "Decision"
    dec_pattern = re.compile(r"((?:decision|recommendation|conclusion|key takeaway|final verdict|verdict|summary))[\s\*:]*(.*)", re.I)
    for idx, line in enumerate(lines):
        m = dec_pattern.search(line)
        if m:
            decision_label = m.group(1).strip("*_ ").title()
            val = m.group(2).strip("*: ")
            if not val and idx + 1 < len(lines):
                val = lines[idx + 1].strip("*: ")
            if val:
                decision = re.sub(r"[\*_]+", "", val).strip()
                break

    # 4. Priority-budget assembly
    reserved_parts = []
    if topic:
        reserved_parts.append(f"[Topic: {topic[:60]}]")
    if decision:
        reserved_parts.append(f"[{decision_label}: {decision[:120]}]")

    reserved_str = " | ".join(reserved_parts)
    remaining_budget = effective_limit - len(reserved_str) - 6

    middle_parts = []
    if first_body and (not topic or first_body != topic) and remaining_budget > 60:
        intro_budget = min(110, remaining_budget // 3)
        intro_text = first_body[:intro_budget] + ("..." if len(first_body) > intro_budget else "")
        middle_parts.append(intro_text)
        remaining_budget -= len(intro_text) + 3

    max_items = 5 if is_most_recent else 3
    if items and remaining_budget > 40:
        added_items = []
        for i, it in enumerate(items[:max_items]):
            item_str = f"{i+1}. {it}"
            if len("; ".join(added_items + [item_str])) + 15 <= remaining_budget:
                added_items.append(item_str)
            else:
                break
        if added_items:
            middle_parts.append("Points: " + "; ".join(added_items))

    all_components = []
    if topic:
        all_components.append(f"[Topic: {topic[:60]}]")
    all_components.extend(middle_parts)
    if decision:
        all_components.append(f"[{decision_label}: {decision[:120]}]")

    summary = " | ".join(all_components)
    if len(summary) > effective_limit:
        summary = summary[:effective_limit-3].rstrip() + "..."
    return summary if summary else cleaned[:effective_limit].rstrip() + "..."

def get_thread_context_str(thread_id: Optional[str], max_turns: int = 6, max_assistant_chars: int = 350) -> str:
    """
    Retrieves bounded conversation history for context injection.
    - Preserves user queries 100% uncompressed.
    - Uses structured compression for assistant responses to preserve entities, options, and decisions
      without runaway token growth or additional LLM calls.
    - Grants 2x recency budget for the immediate prior assistant turn (t_-1) to resolve follow-ups.
    """
    if not thread_id:
        return "No prior conversational context."
    _ensure_thread_history_loaded(thread_id, max_turns=max_turns)
    if thread_id not in thread_histories:
        return "No prior conversational context."
    history = thread_histories[thread_id][-max_turns:]
    lines = []
    
    # Identify index of the most recent assistant turn
    last_asst_idx = -1
    for idx in range(len(history) - 1, -1, -1):
        if history[idx].get("role") != "user":
            last_asst_idx = idx
            break

    for idx, h in enumerate(history):
        role = h.get("role")
        content = h.get("content", "").strip()
        if not content:
            continue
        if role == "user":
            lines.append(f"User: {content}")
        else:
            is_most_recent = (idx == last_asst_idx)
            compact = compress_assistant_turn(content, max_chars=max_assistant_chars, is_most_recent=is_most_recent)
            lines.append(f"Assistant: {compact}")
    return "\n".join(lines) if lines else "No prior conversational context."

def record_thread_turn(thread_id: Optional[str], role: str, content: str):
    """Records turn into the thread's memory cache."""
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
    if not thread_id:
        return ""
    _ensure_thread_history_loaded(thread_id, max_turns=6)
    if thread_id not in thread_histories:
        return ""
    for turn in reversed(thread_histories[thread_id]):
        if turn.get("role") == "user":
            c = turn.get("content", "").strip()
            if c:
                return c
    return ""
