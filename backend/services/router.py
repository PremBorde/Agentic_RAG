import re
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple

from backend.tools import (
    detect_multi_intent,
    detect_gmail_intent,
    detect_calendar_intent,
    detect_task_intent,
    detect_memory_intent,
    is_explicit_web_search,
    is_web_search_continuation,
    extract_web_search_query_and_timeframe,
    detect_image_search_intent,
    is_followup_query,
)

logger = logging.getLogger("router")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class QueryIntent(str, Enum):
    CONVERSATIONAL = "conversational"
    DOCUMENT_RAG = "document_rag"
    GMAIL = "gmail"
    CALENDAR = "calendar"
    TASK = "task"
    MEMORY = "memory"
    WEB_SEARCH = "web_search"
    IMAGE_SEARCH = "image_search"
    MULTI_STEP = "multi_step"
    GENERAL_KNOWLEDGE = "general_knowledge"
    UNKNOWN = "unknown"

@dataclass
class RoutingDecision:
    intent: QueryIntent
    sub_action: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    is_fast_path: bool = False
    is_welcome_card: bool = False
    confidence: float = 1.0
    reason: str = ""
    selected_path: str = ""
    rag_invoked: bool = False
    tools_selected: List[str] = field(default_factory=list)

# ── EXACT NORMALIZED CONVERSATIONAL DICTIONARIES (RULE A) ────────────────────
EXACT_WELCOME_GREETINGS = {
    "hi", "hello", "hey", "greetings", "howdy", "hola", "namaste", "yo", "sup",
    "good morning", "good afternoon", "good evening", "good day", "good night",
    "hi there", "hello there", "hey there", "hello assistant", "hi bot", "hello bot", "hey assistant"
}

EXACT_CAPABILITIES = {
    "what can you do", "who are you", "what are you", "what do you do",
    "tell me about yourself", "how can you help", "who made you", "what is this app", "help me"
}

EXACT_GRATITUDE = {
    "thanks", "thank you", "thx", "ty", "many thanks", "appreciate it",
    "thank you so much", "thanks a lot", "thank you very much"
}

EXACT_FAREWELLS = {
    "bye", "goodbye", "cya", "see you", "take care", "have a good day", "see you later"
}

EXACT_STATUS = {
    "how are you", "how are you doing", "what s up", "whats up", "how do you do",
    "how s it going", "hows it going", "how are things"
}

EXACT_ACKNOWLEDGMENTS = {
    "ok", "okay", "cool", "great", "awesome", "nice", "got it", "sure",
    "sounds good", "alright", "perfect", "done", "understood"
}

EXACT_DECLINATIONS = {
    "no", "nope", "nah", "nothing", "not really", "not now", "not yet",
    "im good", "i m good", "all good", "nevermind", "never mind", "cancel", "none"
}

# Substantive trigger words that must NEVER be treated as small talk (Rule B)
DOCUMENT_KEYWORDS = {
    "document", "documents", "doc", "docs", "pdf", "pdfs", "file", "files",
    "docx", "csv", "json", "note", "notes", "transcript", "transcripts", "youtube",
    "chapter", "chapters", "slide", "slides", "section", "sections", "page", "pages",
    "paper", "papers", "report", "reports", "article", "articles", "manual", "handbook",
    "contract", "contracts", "agreement", "agreements", "policy", "policies",
    "record", "records", "table", "dataset", "corpus", "uploaded", "attachment", "attachments",
    "coursework", "syllabus", "assignment", "assignments", "guideline", "guidelines",
    "question", "questions", "exam", "exams", "endsem", "midsem", "test", "tests",
    "quiz", "quizzes", "study", "curriculum", "module", "modules", "unit", "units",
    "revision", "imp", "important", "problem", "problems", "exercise", "exercises",
    "solution", "solutions", "summary", "summaries", "qa", "qna"
}

SUBSTANTIVE_ACTION_VERBS = {
    "prepare", "explain", "summarize", "analyze", "find", "search", "list",
    "show", "schedule", "create", "draft", "send", "book", "complete", "solve",
    "extract", "calculate", "compare", "translate", "write", "implement", "review"
}

def is_elongated_greeting(word: str) -> bool:
    """Checks if a single word is an elongated greeting (e.g. heyyyy, hiiiii, hellooo)."""
    return bool(
        re.match(r"^h+e+y+$", word) or
        re.match(r"^h+e+l+o+$", word) or
        re.match(r"^h+i+$", word)
    )

def strip_greeting_prefix(text: str) -> Tuple[Optional[str], str]:
    """
    Separates a polite greeting prefix from any substantive prompt.
    E.g.:
      "Hi, explain DAA" -> ("hi", "explain DAA")
      "Good morning, check my emails" -> ("good morning", "check my emails")
      "Thanks, now summarize this document" -> ("thanks", "now summarize this document")
      "No, explain the previous answer" -> ("no", "explain the previous answer")
      "Hello" -> ("hello", "")
    """
    cleaned = text.strip()
    
    # Check 2-word greetings first
    for prefix in ["good morning", "good afternoon", "good evening", "good day", "thank you", "never mind"]:
        pattern = rf"^{prefix}[\s,.:;!?-]+(.*)$"
        m = re.match(pattern, cleaned, re.IGNORECASE)
        if m:
            return prefix, m.group(1).strip()

    # Check 1-word greetings / prefixes
    single_starters = [
        "hi", "hello", "hey", "greetings", "howdy", "hola", "namaste", "yo", "sup",
        "thanks", "thx", "ty", "no", "nope", "nah", "ok", "okay", "cool", "sure"
    ]
    for starter in single_starters:
        pattern = rf"^{starter}[\s,.:;!?-]+(.*)$"
        m = re.match(pattern, cleaned, re.IGNORECASE)
        if m:
            return starter, m.group(1).strip()

    # Check elongated single-word greetings
    words = cleaned.split()
    if words and is_elongated_greeting(words[0].lower().rstrip(",.:;!?")):
        rest = " ".join(words[1:]).strip()
        return words[0].lower(), rest

    return None, cleaned

def classify_query(
    query: str, 
    doc_count: int = 0, 
    has_history: bool = False,
    chat_history_str: str = ""
) -> RoutingDecision:
    """
    Centralized intent classification and routing decision.
    Ensures that substantive requests are NEVER hijacked by conversational fast paths.
    """
    query_clean = query.strip()
    if not query_clean:
        decision = RoutingDecision(
            intent=QueryIntent.CONVERSATIONAL,
            is_fast_path=True,
            is_welcome_card=True,
            reason="Empty query defaults to welcome conversational state",
            selected_path="zero_llm_greeting"
        )
        _log_routing(query, decision)
        return decision

    # Step 1: Input Normalization
    normalized = re.sub(r'[^\w\s]', ' ', query_clean).lower()
    norm_words = normalized.split()
    norm_text = " ".join(norm_words)
    norm_set = set(norm_words)

    # Step 2: Separate possible conversational prefix from payload
    prefix, remainder = strip_greeting_prefix(query_clean)
    remainder_norm = re.sub(r'[^\w\s]', ' ', remainder).lower()
    rem_words = remainder_norm.split()
    rem_set = set(rem_words)

    # Effective query to evaluate for substantive intent
    effective_text = remainder if remainder else query_clean
    effective_norm = remainder_norm if remainder else norm_text
    effective_set = rem_set if remainder else norm_set
    effective_words = rem_words if remainder else norm_words

    # Step 3: Check Multi-Intent Agent Orchestration (highest tool priority)
    multi_intent = detect_multi_intent(effective_text) or detect_multi_intent(query_clean)
    if multi_intent:
        multi_type, multi_params = multi_intent
        tools = ["gmail", "calendar"] if multi_type == "email_and_calendar" else ["gmail", "tasks"]
        decision = RoutingDecision(
            intent=QueryIntent.MULTI_STEP,
            sub_action=multi_type,
            params=multi_params,
            is_fast_path=False,
            is_welcome_card=False,
            reason=f"Detected multi-step compound instruction ({multi_type})",
            selected_path="agent_orchestrator",
            rag_invoked=False,
            tools_selected=tools
        )
        _log_routing(query, decision)
        return decision

    # Step 3b: Check Post-Connection / Action Continuation & Confirmation Queries
    # Check Web Search Confirmation & Follow-up Execution (e.g. "Yes please search and send me the answer", "Search and send me the answer")
    if is_web_search_continuation(effective_text, chat_history_str=chat_history_str) or is_web_search_continuation(query_clean, chat_history_str=chat_history_str):
        resolved_q, resolved_tf = extract_web_search_query_and_timeframe(query_clean, chat_history_str=chat_history_str)
        decision = RoutingDecision(
            intent=QueryIntent.WEB_SEARCH,
            sub_action="web_search_followup",
            params={"query": resolved_q, "timeframe": resolved_tf, "is_continuation": True},
            is_fast_path=False,
            is_welcome_card=False,
            reason=f"User confirmed execution of pending web search for '{resolved_q}' (timeframe: {resolved_tf})",
            selected_path="web_search",
            rag_invoked=False,
            tools_selected=["web_search"]
        )
        _log_routing(query, decision)
        return decision
    t_query = query_clean.lower()

    # Check confirmation follow-ups (e.g. "Yes sure", "Yes please", "Sure", "Go ahead", "Confirm", "Yes")
    confirm_patterns = ["yes sure", "yes plz", "yes please", "sure", "confirm", "go ahead", "do it", "yes add it", "yes do it", "yes book it"]
    is_confirmation = any(t_query == cp or t_query.startswith(cp) for cp in confirm_patterns)
    if is_confirmation and chat_history_str:
        hist_lower = chat_history_str.lower()
        if any(w in hist_lower for w in ["calendar", "calender", "event", "meeting", "focusing", "book it", "schedule"]):
            decision = RoutingDecision(
                intent=QueryIntent.CALENDAR,
                sub_action="create_event",
                params={"prompt": chat_history_str},
                is_fast_path=False,
                is_welcome_card=False,
                reason="Confirmation follow-up routed to Calendar create_event",
                selected_path="calendar_service",
                rag_invoked=False,
                tools_selected=["calendar"]
            )
            _log_routing(query, decision)
            return decision

    # E.g.: "Now i had connected", "Do check now", "Check now", "Now check", "Try now", "Connected now check"
    continuation_patterns = [
        "do check now", "now check", "check now", "check again", "try now", "try again",
        "now i had connected", "now i have connected", "now i connected", "i had connected",
        "i have connected", "i connected", "connected now", "done connecting", "account connected",
        "fetch now", "read now", "do it now", "check please", "please check now"
    ]
    is_continuation = any(p in t_query for p in continuation_patterns) or (
        any(w in t_query for w in ["connect", "link", "done"]) and any(w in t_query for w in ["now", "had", "have", "again"])
    )

    if is_continuation:
        hist_lower = chat_history_str.lower() if chat_history_str else ""
        if any(w in hist_lower for w in ["calendar", "meeting", "meetings", "event", "schedule"]):
            decision = RoutingDecision(
                intent=QueryIntent.CALENDAR,
                sub_action="list_events",
                params={"prompt": query_clean},
                is_fast_path=False,
                is_welcome_card=False,
                reason="Post-connection / follow-up recheck routed to Google Calendar",
                selected_path="calendar_service",
                rag_invoked=False,
                tools_selected=["calendar"]
            )
            _log_routing(query, decision)
            return decision
        else:
            # Route to Gmail search when emails were requested or general post-connection check
            decision = RoutingDecision(
                intent=QueryIntent.GMAIL,
                sub_action="search_emails",
                params={"query": "", "max_results": 5},
                is_fast_path=False,
                is_welcome_card=False,
                reason="Post-connection / follow-up recheck routed to Gmail inbox",
                selected_path="gmail_service",
                rag_invoked=False,
                tools_selected=["gmail"]
            )
            _log_routing(query, decision)
            return decision

    # Step 4: Check Explicit Single-Tool Intents
    # 4a. Gmail Intent
    gmail_intent = detect_gmail_intent(effective_text) or detect_gmail_intent(query_clean)
    if gmail_intent:
        action_name, params = gmail_intent
        decision = RoutingDecision(
            intent=QueryIntent.GMAIL,
            sub_action=action_name,
            params=params,
            is_fast_path=False,
            is_welcome_card=False,
            reason=f"Detected Gmail action intent ({action_name})",
            selected_path="gmail_service",
            rag_invoked=False,
            tools_selected=["gmail"]
        )
        _log_routing(query, decision)
        return decision

    # 4b. Calendar Intent
    cal_intent = detect_calendar_intent(effective_text) or detect_calendar_intent(query_clean)
    if cal_intent:
        action_name, params = cal_intent
        decision = RoutingDecision(
            intent=QueryIntent.CALENDAR,
            sub_action=action_name,
            params=params,
            is_fast_path=False,
            is_welcome_card=False,
            reason=f"Detected Google Calendar intent ({action_name})",
            selected_path="calendar_service",
            rag_invoked=False,
            tools_selected=["calendar"]
        )
        _log_routing(query, decision)
        return decision

    # 4c. Task Intent
    task_intent = detect_task_intent(effective_text) or detect_task_intent(query_clean)
    if task_intent:
        action_name, params = task_intent
        decision = RoutingDecision(
            intent=QueryIntent.TASK,
            sub_action=action_name,
            params=params,
            is_fast_path=False,
            is_welcome_card=False,
            reason=f"Detected Task & Reminder intent ({action_name})",
            selected_path="task_manager",
            rag_invoked=False,
            tools_selected=["tasks"]
        )
        _log_routing(query, decision)
        return decision

    # 4d. Memory Intent
    mem_intent = detect_memory_intent(effective_text) or detect_memory_intent(query_clean)
    if mem_intent:
        action_name, params = mem_intent
        decision = RoutingDecision(
            intent=QueryIntent.MEMORY,
            sub_action=action_name,
            params=params,
            is_fast_path=False,
            is_welcome_card=False,
            reason=f"Detected long-term memory intent ({action_name})",
            selected_path="long_term_memory",
            rag_invoked=False,
            tools_selected=["memory"]
        )
        _log_routing(query, decision)
        return decision

    # 4e. Explicit Web Search Intent
    if is_explicit_web_search(effective_text) or is_explicit_web_search(query_clean):
        q_target = effective_text if is_explicit_web_search(effective_text) else query_clean
        clean_q, tf = extract_web_search_query_and_timeframe(q_target, chat_history_str=chat_history_str)
        decision = RoutingDecision(
            intent=QueryIntent.WEB_SEARCH,
            sub_action="web_search",
            params={"query": clean_q, "timeframe": tf},
            is_fast_path=False,
            is_welcome_card=False,
            reason=f"User explicitly requested live web/internet search for '{clean_q}' (timeframe: {tf})",
            selected_path="web_search",
            rag_invoked=False,
            tools_selected=["web_search"]
        )
        _log_routing(query, decision)
        return decision

    # 4f. Web Image Search Intent
    img_intent = detect_image_search_intent(effective_text, chat_history_str=chat_history_str) or detect_image_search_intent(query_clean, chat_history_str=chat_history_str)
    if img_intent:
        action_name, img_params = img_intent
        reason_str = f"Image search requires entity clarification for '{img_params.get('pronoun')}'" if img_params.get("needs_clarification") else f"User requested images/diagrams/visuals: '{img_params.get('search_query')}'"
        decision = RoutingDecision(
            intent=QueryIntent.IMAGE_SEARCH,
            sub_action=action_name,
            params=img_params,
            is_fast_path=False,
            is_welcome_card=False,
            reason=reason_str,
            selected_path="web_image_search",
            rag_invoked=False,
            tools_selected=["image_search"]
        )
        _log_routing(query, decision)
        return decision

    # Step 5: Check Document & Knowledge RAG Requests
    has_doc_keyword = bool(effective_set & DOCUMENT_KEYWORDS)
    
    # Phrases explicitly pointing to uploaded files or notes (domain-agnostic)
    explicit_doc_triggers = [
        "in the document", "from my document", "in the pdf", "from the pdf",
        "in my notes", "from my notes", "in the file", "from the file",
        "uploaded file", "uploaded doc", "indexed doc", "according to the doc",
        "according to the document", "according to the file", "in section",
        "on page", "in chapter", "from the report", "in the contract",
        "in the table", "from the dataset", "in the article", "from the notes"
    ]
    has_doc_phrase = any(p in effective_norm for p in explicit_doc_triggers)
    is_doc_followup = bool(doc_count > 0 and is_followup_query(effective_text) and chat_history_str and any(k in chat_history_str.lower() for k in ["document", "pdf", "notes", "file", "chunk", "page", "source"]))

    # Dynamic matching against active document filenames in the user's Knowledge Base
    matches_indexed_doc = False
    if doc_count > 0:
        try:
            from backend.vector_store import indexed_documents
            q_low = effective_norm.lower()
            q_tokens = set(re.findall(r'[a-zA-Z0-9_\-]+', q_low))
            STOP_TOKENS = {"and", "the", "for", "with", "from", "list", "detail", "details", "merged", "pdf", "docx", "txt", "md", "csv", "json"}
            for idoc in indexed_documents:
                t = idoc.get("title", "").strip().lower()
                if not t:
                    continue
                base_name = os.path.splitext(t)[0]
                if t in q_low or (len(base_name) > 3 and base_name in q_low):
                    matches_indexed_doc = True
                    break
                doc_tokens = [tok for tok in re.findall(r'[a-zA-Z0-9_\-]+', base_name) if len(tok) >= 3 and tok not in STOP_TOKENS]
                if any(dt in q_tokens or any(dt in qt for qt in q_tokens if len(dt) >= 4) for dt in doc_tokens):
                    matches_indexed_doc = True
                    break
        except Exception:
            pass

    if (has_doc_keyword or has_doc_phrase or is_doc_followup or matches_indexed_doc) and doc_count > 0:
        decision = RoutingDecision(
            intent=QueryIntent.DOCUMENT_RAG,
            is_fast_path=False,
            is_welcome_card=False,
            reason="Explicit document or study request with indexed documents available",
            selected_path="faiss_document_rag",
            rag_invoked=True,
            tools_selected=["retriever"]
        )
        _log_routing(query, decision)
        return decision

    # Step 6: Pure Conversational Intent (Rule A)
    # MUST be pure small talk with NO remaining substantive action
    is_pure_convo = False
    is_welcome = False
    convo_reason = ""

    # Check exact normalized matches
    if norm_text in EXACT_WELCOME_GREETINGS or (len(norm_words) == 1 and is_elongated_greeting(norm_words[0])):
        is_pure_convo = True
        is_welcome = True
        convo_reason = "Exact welcome greeting"
    elif norm_text in EXACT_CAPABILITIES:
        is_pure_convo = True
        is_welcome = True
        convo_reason = "Exact bot capability inquiry"
    elif norm_text in EXACT_GRATITUDE:
        is_pure_convo = True
        is_welcome = False
        convo_reason = "Exact gratitude small talk"
    elif norm_text in EXACT_FAREWELLS:
        is_pure_convo = True
        is_welcome = False
        convo_reason = "Exact farewell small talk"
    elif norm_text in EXACT_STATUS:
        is_pure_convo = True
        is_welcome = False
        convo_reason = "Exact status inquiry small talk"
    elif norm_text in EXACT_ACKNOWLEDGMENTS:
        is_pure_convo = True
        is_welcome = False
        convo_reason = "Exact acknowledgment pleasantry"
    elif norm_text in EXACT_DECLINATIONS:
        is_pure_convo = True
        is_welcome = False
        convo_reason = "Exact polite declination"

    if is_pure_convo:
        decision = RoutingDecision(
            intent=QueryIntent.CONVERSATIONAL,
            is_fast_path=True,
            is_welcome_card=is_welcome,
            reason=convo_reason,
            selected_path="zero_llm_conversational",
            rag_invoked=False,
            tools_selected=[]
        )
        _log_routing(query, decision)
        return decision

    # Step 7: Fallback for Unknown / Follow-up / General Queries
    if is_followup_query(query_clean):
        hist_lower = chat_history_str.lower() if chat_history_str else ""
        # 7a. Follow-up to prior image search (e.g. "What about Soul Mortal ?", "show more pics")
        if any(w in hist_lower for w in ["image_search", "web_image_search", "image", "images", "photo", "photos", "diagram", "diagrams"]):
            clean_sub = re.sub(r'^(?:what\s+about|how\s+about|and|show|show\s+me)\s+', '', query_clean, flags=re.IGNORECASE).strip(' ?.!').strip()
            if clean_sub:
                decision = RoutingDecision(
                    intent=QueryIntent.IMAGE_SEARCH,
                    sub_action="image_search",
                    params={"search_query": clean_sub, "is_diagram": False},
                    is_fast_path=False,
                    is_welcome_card=False,
                    reason=f"Follow-up image search referencing prior visual context: '{clean_sub}'",
                    selected_path="web_image_search",
                    rag_invoked=False,
                    tools_selected=["image_search"]
                )
                _log_routing(query, decision)
                return decision

        # 7b. Follow-up referencing active documents
        if doc_count > 0:
            decision = RoutingDecision(
                intent=QueryIntent.DOCUMENT_RAG,
                is_fast_path=False,
                is_welcome_card=False,
                reason="Follow-up query routed to RAG with active index",
                selected_path="faiss_document_rag",
                rag_invoked=True,
                tools_selected=["retriever"]
            )
            _log_routing(query, decision)
            return decision

    decision = RoutingDecision(
        intent=QueryIntent.GENERAL_KNOWLEDGE,
        is_fast_path=False,
        is_welcome_card=False,
        reason="General knowledge query routed to conversational LLM",
        selected_path="general_llm_assistant",
        rag_invoked=False,
        tools_selected=[]
    )
    _log_routing(query, decision)
    return decision

def _log_routing(raw_query: str, decision: RoutingDecision) -> None:
    """Logs structured routing telemetry without exposing sensitive content."""
    # Sanitize query for logging (limit preview length, omit any emails or credentials)
    sanitized = re.sub(r'[\r\n]+', ' ', raw_query).strip()
    if len(sanitized) > 60:
        sanitized = sanitized[:57] + "..."
    # Obfuscate email addresses if present
    sanitized = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[EMAIL]', sanitized)

    normalized_preview = re.sub(r'[^\w\s]', ' ', raw_query).lower().strip()
    if len(normalized_preview) > 60:
        normalized_preview = normalized_preview[:57] + "..."

    logger.info(f"[ROUTER] Query received: \"{sanitized}\"")
    logger.info(f"[ROUTER] Normalized query: \"{normalized_preview}\"")
    logger.info(f"[ROUTER] Detected intent: QueryIntent.{decision.intent.value.upper()}")
    logger.info(f"[ROUTER] Classification reason: {decision.reason}")
    logger.info(f"[ROUTER] Selected execution path: {decision.selected_path}")
    logger.info(f"[ROUTER] RAG invoked: {decision.rag_invoked}")
    logger.info(f"[ROUTER] Tools selected: {decision.tools_selected}")
    logger.info(f"[ROUTER] Fast path: {decision.is_fast_path}")

