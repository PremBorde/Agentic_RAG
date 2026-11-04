"""
Intelligent Query Processing Engine for RAG
Performs:
1. Query Normalization & Noise Cleaning (stripping filler without altering semantic intent)
2. Technical Terminology & Identifier Preservation (e.g. DAA-1, 0/1 knapsack, ML-3, KNN, SVM)
3. Contextual Follow-Up Resolution (resolving pronouns & continuations using conversation history)
4. Target Document Filtering (detecting explicit mentions of document titles or title keywords)
"""

import re
from typing import Dict, Any, Optional, Tuple, List

# Common filler prefixes in conversational document search
CONVERSATIONAL_PREFIXES = [
    r"^can you (?:tell|explain|summarize|find|show) (?:me )?(?:about )?",
    r"^could you (?:tell|explain|summarize|find|show) (?:me )?(?:about )?",
    r"^please (?:explain|tell|find|search|summarize) (?:me )?(?:about )?",
    r"^from (?:the|my) (?:uploaded )?(?:document|pdf|notes|file|syllabus) (?:can you )?",
    r"^in (?:the|my) (?:uploaded )?(?:document|pdf|notes|file|syllabus) (?:what is|how to|explain)?",
    r"^according to (?:the|my) (?:document|pdf|notes|syllabus) ",
    r"^what does (?:the|my) (?:document|pdf|file) say about ",
    r"^tell me about ",
    r"^explain ",
    r"^what is ",
    r"^what are "
]

def clean_query_text(query: str) -> str:
    """Removes conversational noise while strictly preserving technical search terms."""
    if not query:
        return ""
    q = query.strip()
    
    # Strip question mark and punctuation at the end
    q = re.sub(r'[\?\.!]+$', '', q).strip()

    # Remove polite words and collapse multiple spaces
    q = re.sub(r'\b(?:please|plz|thanks|thank you)\b', '', q, flags=re.IGNORECASE)
    q = re.sub(r'\s+', ' ', q).strip()

    # If query is very short, keep it
    if len(q.split()) <= 2:
        return q

    # Check and strip prefixes
    for pattern in CONVERSATIONAL_PREFIXES:
        m = re.match(pattern, q, flags=re.IGNORECASE)
        if m:
            candidate = q[m.end():].strip()
            # Only keep stripped version if it has substantive content
            if len(candidate.split()) >= 1:
                q = candidate
                break

    return q.strip()

def resolve_contextual_query(
    current_query: str,
    chat_history_str: str = "",
    last_query: str = ""
) -> str:
    """
    Expands ambiguous or follow-up queries using previous topic context.
    E.g.
    Previous: "Explain fractional knapsack"
    Current: "What is its time complexity?" -> "fractional knapsack What is its time complexity?"
    """
    cleaned = clean_query_text(current_query)
    curr_lower = cleaned.lower()

    # Check if current query is a short follow-up or has relative pronouns
    is_followup = any(curr_lower.startswith(w) for w in [
        "what about", "how about", "explain the next", "next topic", "next practical",
        "and its", "its time complexity", "time complexity of it", "more details on that",
        "tell me more", "the previous one", "in hinglish", "in hindi", "summarize that"
    ]) or any(p in curr_lower for p in [" it ", " its ", " that ", " this "])

    if is_followup and last_query:
        cleaned_last = clean_query_text(last_query)
        return f"{cleaned_last} {cleaned}".strip()

    return cleaned

def extract_document_filter(query: str, available_doc_names: List[str]) -> Optional[str]:
    """Detects if user explicitly named an available document or prominent title segment."""
    q_lower = query.lower()
    for doc_name in available_doc_names:
        # Check full doc name
        if doc_name.lower() in q_lower:
            return doc_name
        # Check base name without extension
        base = re.sub(r'\.[a-zA-Z0-9]+$', '', doc_name).strip().lower()
        if len(base) >= 3 and base in q_lower:
            return doc_name
        # Check key multi-word title prefixes (e.g. "computer science fundamentals")
        base_words = [w for w in re.split(r'[\s&_\-]+', base) if len(w) > 2]
        if len(base_words) >= 2:
            two_word_prefix = " ".join(base_words[:2])
            three_word_prefix = " ".join(base_words[:3]) if len(base_words) >= 3 else ""
            if three_word_prefix and three_word_prefix in q_lower:
                return doc_name
            if two_word_prefix and two_word_prefix in q_lower:
                return doc_name
    return None
