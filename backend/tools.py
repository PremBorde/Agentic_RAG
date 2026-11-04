import re
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from langchain_community.tools import DuckDuckGoSearchRun

web_search_tool = DuckDuckGoSearchRun()

GREETING_PATTERNS = [
    r"^(hi|hello|hey|greetings|howdy|hola|namaste|yo|sup)(\s+.*)?$",
    r"^how\s+are\s+you(\s+.*)?$",
    r"^(good\s+morning|good\s+afternoon|good\s+evening|good\s+night|good\s+day)(\s+.*)?$",
    r"^(thanks|thank\s+you|thx|ty|many\s+thanks)(\s+.*)?$",
    r"^(who\s+are\s+you|what\s+are\s+you|what\s+can\s+you\s+do|what\s+do\s+you\s+do|help\s+me|tell\s+me\s+about\s+yourself|what\s+is\s+this(\s+app)?)(\s+.*)?$",
    r"^(bye|goodbye|see\s+you|cya|take\s+care)(\s+.*)?$",
    r"^(ok|okay|cool|great|awesome|nice|got\s+it|sure)(\s+.*)?$"
]

def is_conversational_query(text: str) -> bool:
    """
    Delegates to centralized QueryIntent classifier.
    Returns True ONLY if intent is QueryIntent.CONVERSATIONAL with no substantive task.
    """
    from backend.services.router import classify_query, QueryIntent
    decision = classify_query(text)
    return decision.intent == QueryIntent.CONVERSATIONAL

def get_direct_greeting_response(text: str) -> Optional[str]:
    """
    Returns an instant, direct, high-quality conversational response for greetings,
    small talk, and capability inquiries without making an LLM API call.
    """
    if not text:
        return "Hello! How can I assist you today?"

    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', text).lower().strip()

    # 1. Capabilities & About
    if any(k in cleaned for k in [
        "what can you do", "who are you", "what are you", "what do you do",
        "how can you help", "tell me about yourself", "what is this app", "help me"
    ]):
        return (
            "Hello! I am your **Personal AI Agent Studio**, an agentic assistant equipped with tools for:\n\n"
            "- 📄 **Document RAG:** Ingest PDFs, text notes, or YouTube transcripts and query them with source citations.\n"
            "- 📬 **Gmail Management:** Search messages, summarize email threads, and draft new messages.\n"
            "- 📅 **Google Calendar:** Check your schedule, find free meeting slots, and propose events.\n"
            "- 📋 **Tasks & Reminders:** Organize your to-dos, view deadlines, and track overdue tasks.\n"
            "- 🌐 **Live Web Search:** Retrieve real-time internet information and web search results.\n"
            "- 🛡️ **Human-in-the-Loop:** High-impact operations (sending emails, scheduling meetings) require your explicit approval.\n\n"
            "How can I help you today?"
        )

    # 2. Gratitude
    if any(cleaned.startswith(k) for k in ["thanks", "thank you", "thx", "ty", "many thanks", "appreciate"]):
        return "You're very welcome! Let me know if there's anything else you need help with."

    # 3. Farewells
    if any(cleaned.startswith(k) for k in ["bye", "goodbye", "see you", "cya", "take care"]):
        return "Goodbye! Have a great day, and feel free to reach out anytime."

    # 4. Status / How are you
    if any(k in cleaned for k in ["how are you", "how do you do", "what's up", "whats up", "how's it going"]):
        return "I'm doing great, thank you for asking! Everything is loaded and ready. What would you like to explore or work on?"

    # 5. Small Acknowledgments
    if cleaned in ["ok", "okay", "cool", "great", "awesome", "nice", "got it", "sure", "sounds good", "done"]:
        return "Awesome! Let me know what you'd like to do next whenever you're ready."

    # 6. Polite Declinations / Small Negative Responses ("No", "Nope", "Nothing right now")
    negative_starters = [
        "no", "nope", "nah", "nothing", "not really", "not now", "not yet",
        "im good", "i m good", "all good", "nevermind", "never mind", "cancel", "none"
    ]
    if cleaned in negative_starters or any(cleaned.startswith(k + " ") for k in ["no", "nope", "nah", "nothing", "not really", "not now", "im good", "all good", "nevermind", "never mind"]):
        return "No problem at all! I'm right here whenever you need me. Feel free to ask a question, query your documents, or check your tools anytime."

    # 7. General Greetings (Hi, Hello, Hey, Good morning/afternoon/evening)
    greetings = [
        "hi", "hello", "hey", "greetings", "howdy", "hola", "namaste", "yo", "sup",
        "good morning", "good afternoon", "good evening", "good day"
    ]
    words_list = cleaned.split()
    first_w = words_list[0] if words_list else ""
    if (
        first_w in greetings
        or any(cleaned.startswith(g + " ") for g in greetings)
        or re.match(r"^h+e+y+$", first_w)
        or re.match(r"^h+e+l+o+$", first_w)
        or re.match(r"^h+i+$", first_w)
    ):
        now_hour = datetime.now().hour
        time_greeting = "Good morning" if now_hour < 12 else ("Good afternoon" if now_hour < 17 else "Good evening")
        return (
            f"Hello! {time_greeting}. I'm your Personal AI Agent, ready to assist you.\n\n"
            "Here are a few things we can do together:\n"
            "- 📚 **Knowledge Base & RAG:** Upload PDFs, notes, or YouTube transcripts to get grounded answers with source citations.\n"
            "- 📬 **Gmail Management:** Search messages, summarize email threads, or draft professional replies.\n"
            "- 📅 **Google Calendar:** Check your schedule, find free meeting slots, or draft calendar invitations.\n"
            "- 📋 **Tasks & Reminders:** Organize your to-dos, track due dates, and manage overdue tasks.\n"
            "- 🌐 **Live Web Search:** Find current news, research topics, or get real-time facts.\n\n"
            "What would you like to explore or work on right now?"
        )

    return (
        "Hello! Everything is loaded and ready to assist you.\n\n"
        "Here are a few things we can do together:\n"
        "- 📚 **Knowledge Base & RAG:** Query uploaded files, notes, and transcripts.\n"
        "- 📬 **Gmail & Calendar:** Manage emails, check availability, and schedule meetings.\n"
        "- 📋 **Tasks & Memory:** Track to-dos and save persistent preferences.\n"
        "- 🌐 **Live Web Search:** Research current facts and internet data.\n\n"
        "How can I help you today?"
    )

def is_web_search_continuation(text: str, chat_history_str: str = "") -> bool:
    """
    Detects if the user confirms or commands execution of a previously acknowledged/pending web search.
    E.g.: 'Yes please search and send me the answer', 'Search and send me the answer', 'Do the search'.
    """
    t = text.lower().strip().rstrip(".!?,")
    direct_search_commands = [
        "search and send me the answer", "search and send the answer", "search and send",
        "yes please search and send me the answer", "yes please search and send the answer",
        "yes search and send me the answer", "yes search and send the answer", "yes search and send",
        "yes please search", "yes please search now", "yes search", "yes search now",
        "please search and send me the answer", "please search and send", "please search",
        "search now", "do the search", "go ahead and search", "execute the search",
        "search for it", "find and send me the answer", "find and send"
    ]
    if any(t == cmd or t.startswith(cmd) for cmd in direct_search_commands):
        return True

    # Check confirmation when previous turn acknowledged or promised a web search
    confirm_starters = ["yes", "sure", "go ahead", "confirm", "please do", "do it", "ok search", "okay search"]
    is_confirm = any(t == cs or t.startswith(cs + " ") for cs in confirm_starters)
    if is_confirm and chat_history_str:
        hist_lower = chat_history_str.lower()
        search_acknowledgement_cues = [
            "perform a web search", "search the web", "search online",
            "searching the web", "i'll search", "i will search", "web search to fetch",
            "look that up on the web", "check the web"
        ]
        if any(cue in hist_lower for cue in search_acknowledgement_cues):
            return True

    return False


def is_explicit_web_search(text: str) -> bool:
    """Detects if the user explicitly requested live internet / web search."""
    t = text.lower().strip()
    triggers = [
        "web search", "search web", "search the web", "search on web",
        "search the internet", "search internet", "search online", "online search",
        "browse the web", "browse web", "live search", "duckduckgo",
        "google search", "search google", "look up online", "search live",
        "latest news", "today's news", "todays news", "news today", "top news",
        "breaking news", "recent news", "world news", "current news", "trending today",
        "top 5 news", "top 10 news", "news headlines", "headlines today",
        "news from the recent week", "news from recent week", "news from this week",
        "news from last week", "news from the past week", "news from today"
    ]
    if any(trig in t for trig in triggers):
        return True
    if re.search(r'\b(?:web\s*search|search\s*(?:the\s+)?(?:web|internet|online))\b', t):
        return True
    if re.search(r'\b(?:today(?:\x27s)?|current|latest|breaking|recent|top\s*\d*)\s+(?:\w+\s+)?news\b', t) or re.search(r'\b(?:tech|world|market|crypto|ai|space|finance|sports)\s+news\b', t):
        return True
    if re.search(r'\b(?:news|headlines|updates|stories)\s+(?:from|for|in|about|of)\s+(?:the\s+)?(?:recent|past|this|last)\s+(?:week|month|day|year|24\s*hours?|7\s*days?)\b', t):
        return True
    if re.search(r'\b(?:give\s+me|show\s+me|get\s+me|find|fetch)\s+(?:the\s+)?news\s+(?:from|of|for|about)\b', t):
        return True
    if re.search(r'\bnews\s+(?:today|headlines|from|in)\b', t):
        return True
    if re.search(r'\b(?:weather\s+(?:today\s+)?in|stock\s+price|current\s+price\s+of)\b', t):
        return True
    return False


def extract_web_search_query_and_timeframe(query: str, chat_history_str: str = "") -> Tuple[str, Optional[str]]:
    """
    Extracts the core search topic and resolves temporal constraints to DDGS timelimit:
    - 'd': past day / 24 hours / today
    - 'w': past week / recent week / last 7 days
    - 'm': past month / last 30 days
    - 'y': past year
    If query is a follow-up continuation ('search and send me the answer'),
    resolves the pending search topic from chat_history_str.
    """
    q_clean = query.strip()
    q_low = q_clean.lower()

    if is_web_search_continuation(q_clean, chat_history_str=chat_history_str):
        if chat_history_str:
            lines = [l.strip() for l in chat_history_str.split('\n') if l.strip()]
            for line in reversed(lines):
                if line.startswith("User:"):
                    prev_user_q = line[5:].strip()
                    if is_explicit_web_search(prev_user_q):
                        return extract_web_search_query_and_timeframe(prev_user_q, chat_history_str="")
            for line in reversed(lines):
                if line.startswith("Assistant:") and ("search" in line.lower() or "news" in line.lower()):
                    m_ack = re.search(r'(?:search\s+for|search\s+the\s+web\s+for|perform\s+a\s+web\s+search\s+to\s+fetch|fetch\s+the)\s+([^\.]+)', line, re.I)
                    if m_ack:
                        ack_topic = m_ack.group(1).strip()
                        tf = "w" if "week" in line.lower() else ("d" if "today" in line.lower() or "day" in line.lower() else None)
                        return ack_topic, tf

    timeframe = None
    if re.search(r'\b(?:today|last\s+24\s*hours?|past\s+24\s*hours?|past\s+day|last\s+day|24h|recent\s+24\s*hours?)\b', q_low):
        timeframe = "d"
    elif re.search(r'\b(?:recent\s+week|this\s+week|past\s+week|last\s+week|last\s+7\s*days?|past\s+7\s*days?|7\s*days?|1\s*week|this\s+past\s+week|the\s+recent\s+week)\b', q_low):
        timeframe = "w"
    elif re.search(r'\b(?:recent\s+month|this\s+month|past\s+month|last\s+month|last\s+30\s*days?|30\s*days?|1\s*month)\b', q_low):
        timeframe = "m"
    elif re.search(r'\b(?:this\s+year|past\s+year|last\s+year)\b', q_low):
        timeframe = "y"

    clean_q = q_clean
    clean_q = re.sub(
        r'^(?:please\s+)?(?:can\s+you\s+)?(?:could\s+you\s+)?(?:search\s+(?:the\s+)?(?:web|internet|online)\s+(?:for\s+)?|web\s*search\s+(?:for\s+)?|browse\s+(?:the\s+)?web\s+(?:for\s+)?|google\s+(?:for\s+)?|give\s+me\s+|tell\s+me\s+|show\s+me\s+|find\s+me\s+|get\s+me\s+|fetch\s+me\s+|provide\s+me\s+|look\s+up\s+|search\s+for\s+|search\s+|browse\s+|for\s+)',
        '', clean_q, flags=re.IGNORECASE
    )
    clean_q = re.sub(r'\b(?:from|in|during|over)\s+(?:the\s+)?(?:recent|past|this|last)\s+(?:week|month|day|year|24\s*hours?|7\s*days?|30\s*days?)\b', '', clean_q, flags=re.IGNORECASE)
    clean_q = re.sub(r'\b(?:from|of)\s+(?:the\s+)?(?:recent\s+week|this\s+week|past\s+week|last\s+week|today|yesterday)\b', '', clean_q, flags=re.IGNORECASE)
    clean_q = re.sub(r'\b(?:this\s+week|recent\s+week|past\s+week|last\s+week|today|yesterday)\b', '', clean_q, flags=re.IGNORECASE)
    clean_q = re.sub(r'[\?\.!]+$', '', clean_q).strip()

    if not clean_q or len(clean_q) < 2:
        clean_q = q_clean

    return clean_q, timeframe

FORBIDDEN_SEARCH_TERMS = {
    # Pronouns & determiners
    "his", "her", "its", "their", "them", "him", "he", "she", "it", "they", "this", "that", "these", "those",
    # Single action/filler terms
    "show", "find", "get", "give", "display", "fetch", "search", "look", "look up", "provide",
    "image", "images", "img", "imgs", "pic", "pics", "picture", "pictures", "photo", "photos", "photograph", "photographs",
    "diagram", "diagrams", "schematic", "schematics", "visual", "visuals", "wallpaper", "wallpapers", "logo", "logos",
    # Naive fragments
    "can you show", "can you show his", "can you show her", "can you show its", "can you show their",
    "show me", "show me his", "show me her", "show me its", "show me their",
    "show his", "show her", "show its", "show their",
    "find his", "find her", "find its", "find their",
    "get his", "get her", "get its", "get their",
    "his img", "her img", "its img", "their img",
    "his image", "her image", "its image", "their image",
    "his photo", "her photo", "its photo", "their photo",
    "his pic", "her pic", "its pic", "their pic",
    "again", "once more", "some", "a", "an", "the"
}

MALE_NAMES = {
    "sam", "elon", "sundar", "satya", "bill", "steve", "jeff", "mark", "larry", "sergey", 
    "alan", "albert", "richard", "guido", "linus", "john", "paul", "george", "james", 
    "robert", "michael", "david", "william", "altman", "musk"
}
FEMALE_NAMES = {
    "marie", "ada", "grace", "fei-fei", "mira", "sheryl", "lisa", "susan", "margaret", 
    "katherine", "hedy", "rosalind", "barbara", "curie"
}
SYSTEM_TOKENS = {
    "user", "assistant", "human", "ai", "model", "system", "response", "question", 
    "answer", "here", "note", "context", "image", "images", "diagram", "references",
    "can", "could", "would", "should", "may", "might", "will", "shall", "must",
    "do", "does", "did", "is", "are", "was", "were", "have", "has", "had",
    "show", "find", "tell", "give", "display", "what", "who", "where", "when", "why", "how",
    "please", "thanks", "thank", "hello", "hi", "hey"
}

def resolve_entity_by_pronoun(pronoun: str, history_str: str) -> str:
    """
    Deterministically resolves a pronoun ('his', 'her', 'its', 'their', 'them', 'him') 
    to the correct entity previously introduced in the conversation history (either through 
    general knowledge answers or prior tool interactions).
    Zero external AI calls.
    """
    if not history_str:
        return ""
    p_low = pronoun.lower().strip()

    # Replay / repeat tokens check previous image search query in history
    m_hist = re.search(r"(?:images?|diagrams?|visuals?)\s+retrieved\s+for\s+\*\*([^\*]+)\*\*", history_str, re.I)
    if m_hist and p_low in ["this", "that", "again", "it", "them"]:
        return m_hist.group(1).strip()

    lines = [line.strip() for line in history_str.split("\n") if line.strip()]
    
    # Priority 1: User question subjects (e.g. 'Who is Sam Altman?', 'Tell me about Anthropic', 'Compare Elon Musk and Marie Curie')
    subjects = []
    for line in lines:
        for m in re.finditer(r"(?:who\s+is|what\s+is|tell\s+me\s+about|compare|explain|discuss)\s+([A-Za-z0-9_\-\s]+?)(?:\?|\.|\n|$)", line, re.I):
            sub_raw = m.group(1).strip()
            if " and " in sub_raw.lower():
                parts = re.split(r"\s+and\s+", sub_raw, flags=re.I)
                subjects.extend([p.strip() for p in parts if p.strip()])
            else:
                subjects.append(sub_raw)

    # Priority 2: Multi-word capitalized proper nouns (e.g. Sam Altman, Elon Musk, Marie Curie)
    proper_nouns = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", history_str)

    # Priority 3: Single capitalized nouns
    single_nouns = re.findall(r"\b([A-Z][a-z]{2,})\b", history_str)

    raw_candidates = []
    for s in subjects + proper_nouns + single_nouns:
        s_clean = s.strip()
        if s_clean.lower() not in SYSTEM_TOKENS and len(s_clean) > 2:
            if any(s_clean != c and s_clean in c for c in raw_candidates):
                continue
            if s_clean not in raw_candidates:
                raw_candidates.append(s_clean)

    candidates = []
    for c in raw_candidates:
        if not any(c != other and c in other.split() for other in raw_candidates):
            candidates.append(c)

    if p_low in ["his", "him", "he"]:
        for c in candidates:
            tokens = c.lower().split()
            if any(t in MALE_NAMES for t in tokens):
                return c
            c_esc = re.escape(c)
            if re.search(rf"{c_esc}[^\.\n]{{0,80}}\b(?:he|his|him|himself|man|businessman|entrepreneur|founder|ceo)\b", history_str, re.I):
                return c
        for c in candidates:
            if not any(t in FEMALE_NAMES for t in c.lower().split()):
                return c

    elif p_low in ["her", "hers", "she"]:
        for c in candidates:
            tokens = c.lower().split()
            if any(t in FEMALE_NAMES for t in tokens):
                return c
            c_esc = re.escape(c)
            if re.search(rf"{c_esc}[^\.\n]{{0,80}}\b(?:she|her|hers|herself|woman|female|scientist|physicist)\b", history_str, re.I):
                return c

    elif p_low in ["its", "it", "this", "that"]:
        for c in candidates:
            c_low = c.lower()
            if not any(t in MALE_NAMES or t in FEMALE_NAMES for t in c_low.split()):
                return c

    elif p_low in ["their", "theirs", "them", "they"]:
        if len(candidates) >= 2:
            return " and ".join(candidates[:2])
        if candidates:
            return candidates[0]

    return candidates[0] if candidates else ""

def detect_image_search_intent(text: str, chat_history_str: str = "") -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Detects if the user explicitly requested web images, photos, diagrams, schematics, or visuals.
    Keeps image search completely separate from Document RAG and other tools.
    Supports follow-up queries ("can you show his img?", "show his photo", "show its logo",
    "show them again") via deterministic conversation-history entity resolution.
    Zero external AI calls.
    """
    t = text.lower().strip()
    if not t:
        return None

    # Exclude queries referencing local documents or uploaded files
    doc_refs = [
        "in my doc", "from my doc", "in the doc", "from the doc", 
        "in my pdf", "from my pdf", "in the pdf", "from the pdf",
        "in my notes", "from my notes", "according to my notes", "to my notes",
        "in the syllabus", "from the syllabus", "coursework", "uploaded file", 
        "uploaded document", "in my coursework", "from my coursework"
    ]
    if any(k in t for k in doc_refs):
        return None

    visual_terms = r"(?:images?|imgs?|pictures?|pics?|pix|photos?|photographs?|diagrams?|schematics?|visuals?|wallpapers?|illustrations?|infographics?|figures?|drawings?|logos?)"

    # Check continuation / replay requests (e.g. "show them again", "show it again", "show pics again", "show that again")
    cont_m = re.match(r"^(?:please\s+)?(?:can\s+you\s+)?(?:show|display|get|fetch|find)\s+(?:them|it|these|those|that|pics|pictures|images|diagrams)?\s*(?:again|once more)", t)
    if cont_m:
        prev_q = ""
        if chat_history_str:
            m_hist = re.search(r"(?:images?|diagrams?|visuals?)\s+retrieved\s+for\s+\*\*([^\*]+)\*\*", chat_history_str, re.I)
            if not m_hist:
                m_hist = re.search(r"(?:image|img|pic|picture|diagram)\s+(?:of|for)\s+([^\r\n]+)", chat_history_str, re.I)
            if m_hist:
                prev_q = m_hist.group(1).strip()
            else:
                prev_q = resolve_entity_by_pronoun("that", chat_history_str)
        if prev_q:
            return ("image_search", {"search_query": prev_q, "is_diagram": bool(re.search(r"diagram", t))})
        else:
            return ("image_search", {"search_query": None, "needs_clarification": True, "pronoun": "that", "is_diagram": False})

    # Check possessive pronoun queries: "can you show his img?", "show his photo", "show its logo", "show her image"
    pat_possessive = rf"^(?:please\s+)?(?:can\s+you\s+)?(?:could\s+you\s+)?(?:show|display|get|give|fetch|find)\s+(?:me\s+)?(his|her|its|their|the)\s+{visual_terms}(?:\s+(?:of|for)\s+(.*))?$"
    m_poss = re.match(pat_possessive, t.strip().rstrip("?.!"), re.IGNORECASE)
    if m_poss:
        pronoun = m_poss.group(1).lower()
        trailing = (m_poss.group(2) or "").strip()
        is_diag = bool(re.search(r"\b(?:diagrams?|schematics?|infographics?|illustrations?|architecture)\b", t))
        is_logo = bool(re.search(r"\b(?:logos?|icon|icons)\b", t))

        if trailing and trailing.lower() not in FORBIDDEN_SEARCH_TERMS:
            return ("image_search", {"search_query": trailing, "is_diagram": is_diag})

        resolved = resolve_entity_by_pronoun(pronoun, chat_history_str) if chat_history_str else ""
        if resolved:
            query_res = f"{resolved} logo" if is_logo and "logo" not in resolved.lower() else resolved
            return ("image_search", {"search_query": query_res, "is_diagram": is_diag})
        else:
            return ("image_search", {"search_query": None, "needs_clarification": True, "pronoun": pronoun, "is_diagram": is_diag})

    # Check objective pronoun queries: "show me img of him", "pictures of her", "photo of it"
    pat_objective = rf"^(?:please\s+)?(?:can\s+you\s+)?(?:could\s+you\s+)?(?:show\s+(?:me\s+)?|display\s+|get\s+(?:me\s+)?|find\s+(?:me\s+)?){visual_terms}\s+(?:of|for)\s+(him|her|it|them|this|that)$"
    m_obj = re.match(pat_objective, t.strip().rstrip("?.!"), re.IGNORECASE)
    if m_obj:
        pronoun = m_obj.group(1).lower()
        is_diag = bool(re.search(r"\b(?:diagrams?|schematics?|infographics?|illustrations?|architecture)\b", t))
        resolved = resolve_entity_by_pronoun(pronoun, chat_history_str) if chat_history_str else ""
        if resolved:
            return ("image_search", {"search_query": resolved, "is_diagram": is_diag})
        else:
            return ("image_search", {"search_query": None, "needs_clarification": True, "pronoun": pronoun, "is_diagram": is_diag})

    action_verbs = {"show", "find", "find a", "get", "give", "give me", "display", "fetch", "search", "look up", "provide"}

    action_patterns = [
        # 1. Action requests: show me img of ..., find photos of ..., get pics of ...
        rf"^(?:please\s+)?(?:can\s+you\s+)?(?:could\s+you\s+)?(?:show\s+(?:me\s+)?|find\s+(?:me\s+)?|search\s+(?:for\s+)?|look\s+up\s+|display\s+|get\s+(?:me\s+)?|give\s+(?:me\s+)?|fetch\s+|provide\s+(?:me\s+)?)(?:some\s+)?(?:the\s+)?(?:an\s+|a\s+)?{visual_terms}(?:\s+(?:of|for|about|showing|depicting))?\s*(.*)$",
        # 2. Search commands: image search for ..., img search ..., pic search ...
        rf"^(?:(?:image|img|pic|picture|photo)\s+search(?:\s+for)?)\s*(.*)$",
        # 3. Direct noun phrases: img of ..., pictures of ..., diagram of ...
        rf"^{visual_terms}\s+(?:of|for|about|showing|depicting)\s+(.*)$",
        # 4. Visual guides/reference: visual reference for ...
        r"^(?:visual\s+reference|visual\s+representation|visual\s+guide)\s+(?:for|of|about)\s+(.*)$",
        # 5. Suffix terms: mortal img, cat picture, transformer diagram
        rf"^(.+?)\s+{visual_terms}$"
    ]

    for idx, pat in enumerate(action_patterns):
        m = re.match(pat, t, re.IGNORECASE)
        if m:
            extracted = m.group(1).strip()
            extracted = re.sub(r"[\?\.!]+$", "", extracted).strip()
            extracted = re.sub(r"\b(?:please|plz|thanks|thank you)\b$", "", extracted).strip()

            # If pattern 5 matched only an action verb, it was an imperative without trailing subject
            if idx == 4 and extracted.lower() in action_verbs:
                extracted = ""

            # Check if extracted term is a forbidden fragment or pronoun
            if extracted.lower() in FORBIDDEN_SEARCH_TERMS:
                pron = "that"
                for p in ["his", "her", "its", "their", "him", "them", "it", "this", "that"]:
                    if p in extracted.lower().split():
                        pron = p
                        break
                resolved = resolve_entity_by_pronoun(pron, chat_history_str) if chat_history_str else ""
                if resolved:
                    extracted = resolved
                else:
                    return ("image_search", {"search_query": None, "needs_clarification": True, "pronoun": pron, "is_diagram": False})

            # If extracted is empty or pronoun, resolve from history
            if not extracted or extracted.lower() in ["it", "them", "this", "that", "again"]:
                if chat_history_str:
                    resolved = resolve_entity_by_pronoun("that", chat_history_str)
                    if resolved:
                        extracted = resolved
                    else:
                        return ("image_search", {"search_query": None, "needs_clarification": True, "pronoun": "that", "is_diagram": False})
                else:
                    return ("image_search", {"search_query": None, "needs_clarification": True, "pronoun": "that", "is_diagram": False})

            if extracted and extracted.lower() not in FORBIDDEN_SEARCH_TERMS:
                is_diag = bool(re.search(r"\b(?:diagrams?|schematics?|infographics?|illustrations?|architecture)\b", t))
                return ("image_search", {"search_query": extracted, "is_diagram": is_diag})

    # Catch explicit inline phrases
    inline_m = re.search(rf"\b(?:search\s+(?:for\s+)?{visual_terms}|show\s+(?:me\s+)?(?:some\s+|a\s+|an\s+|the\s+)?{visual_terms})\s+(?:of|for|about)\s+(.+)$", t, re.IGNORECASE)
    if inline_m:
        extracted = inline_m.group(1).strip()
        extracted = re.sub(r"[\?\.!]+$", "", extracted).strip()
        extracted = re.sub(r"\b(?:please|plz|thanks|thank you)\b$", "", extracted).strip()
        if extracted and extracted.lower() not in FORBIDDEN_SEARCH_TERMS:
            is_diag = bool(re.search(r"\b(?:diagrams?|schematics?)\b", t))
            return ("image_search", {"search_query": extracted, "is_diagram": is_diag})

    # Catch multi-clause / compound questions e.g. "Do you know Who is Soul Regaltos ? show me the Img of him"
    clauses = [c.strip() for c in re.split(r"[\?\.!;]+", text) if c.strip()]
    if len(clauses) > 1:
        for idx, clause in enumerate(clauses):
            c_res = detect_image_search_intent(clause, chat_history_str=chat_history_str)
            if c_res:
                _, c_params = c_res
                sq = c_params.get("search_query", "") or ""
                sq_clean = sq.strip().lower()
                if not sq_clean or sq_clean in FORBIDDEN_SEARCH_TERMS:
                    for prev_c in reversed(clauses[:idx]):
                        sub_m = re.search(r"(?:who\s+is|what\s+is|about|know)\s+([A-Za-z0-9\s]+)", prev_c, re.I)
                        if sub_m:
                            c_params["search_query"] = sub_m.group(1).strip()
                            c_params["needs_clarification"] = False
                            return ("image_search", c_params)
                    if chat_history_str:
                        resolved = resolve_entity_by_pronoun("that", chat_history_str)
                        if resolved:
                            c_params["search_query"] = resolved
                            c_params["needs_clarification"] = False
                            return ("image_search", c_params)
                else:
                    return c_res

    return None

def is_followup_query(text: str) -> bool:
    """Detects follow-up questions or commands that explicitly refer to previous topic/context."""
    t = text.lower().strip()
    # Explicit contextual follow-up phrases
    followup_phrases = [
        "the next one", "continue", "elaborate", "tell me more", "what about its",
        "explain more", "more details", "in hinglish", "in hindi", "summarize that",
        "summarize this", "points 2 and 3", "explain that", "what else",
        "previous answer", "previous topic", "as mentioned", "next topic", "next question",
        "explain the previous"
    ]
    if any(p in t for p in followup_phrases):
        return True
        
    # Check if starts with a followup verb without an independent target
    followup_starters = [
        "explain the", "what about", "continue with", "elaborate on",
        "summarize the above", "give more", "tell me more", "how about the",
        "what else", "go on", "keep going"
    ]
    return any(t.startswith(s) for s in followup_starters)

def detect_gmail_intent(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Detects if query targets Gmail: connect, access check, search, read, draft, or send."""
    t = text.lower().strip()

    # 0a. Check Access / Connection Status
    access_triggers = [
        "access to my mail", "access to my email", "access to my gmail",
        "access to email", "access to gmail", "access to mail",
        "have access to my", "can you access my", "do you have access to",
        "are you connected to my mail", "is my mail connected",
        "is my email connected", "is my gmail connected",
        "can you see my mail", "can you see my email", "can you read my mail",
        "can you read my email", "do you see my mail", "do you see my email",
        "access to mail", "access to emails", "access my mail", "access my emails"
    ]
    has_mail_kw = any(w in t for w in ["mail", "email", "emails", "gmail", "inbox"])
    if any(trig in t for trig in access_triggers) and has_mail_kw:
        return ("check_access", {"prompt": text})
    
    # 0. Connect / Authorize / Sign In to Gmail or Google Workspace
    connect_triggers = [
        "connect to gmail", "connect gmail", "link gmail", "sign in to gmail",
        "login to gmail", "log in to gmail", "authenticate gmail", "authorize gmail",
        "integrate gmail", "connect my gmail", "connect email", "connect to email",
        "connect google", "connect google workspace", "need to connect to gmail",
        "how to connect gmail", "how do i connect gmail", "link my gmail",
        "i need to connect to gmail", "i want to connect to gmail", "connect to my gmail"
    ]
    if any(k in t for k in connect_triggers) or (
        any(w in t for w in ["connect", "link", "login", "sign in", "authorize", "authenticate"]) 
        and any(w in t for w in ["gmail", "google workspace", "workspace"])
    ):
        return ("connect_gmail", {})
    
    # 1. Send Email proposal (sensitive action -> proposal)
    if "send an email" in t or "send email" in t or "shoot an email" in t or "send a mail" in t or "mail to" in t:
        # Extract basic parameters
        to_match = re.search(r"(?:to\s+)?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", text, re.IGNORECASE)
        to_email = to_match.group(1) if to_match else "recipient@example.com"
        
        subj = None
        subj_match = re.search(r"subject\s+['\"]?([^'\"\n,]+)['\"]?", text, re.IGNORECASE)
        if subj_match:
            subj = subj_match.group(1).strip()
        else:
            topic_match = re.search(r"(?:regarding|about|for|wishing)\s+(?:a\s+)?([a-zA-Z0-9\s]+?)(?:\s+plz|\s+please|\s+to|\.|\n|$)", text, re.IGNORECASE)
            if topic_match:
                subj = topic_match.group(1).strip().title()
        if not subj:
            subj = "Email Message"
            
        return ("send_email", {"to": to_email, "subject": subj, "prompt": text})
        
    # 2. Draft Email
    if "draft an email" in t or "draft email" in t or "create a draft" in t or "write a draft" in t:
        to_match = re.search(r"to\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", text, re.IGNORECASE)
        to_email = to_match.group(1) if to_match else "team@example.com"
        return ("create_draft", {"to": to_email, "prompt": text})
        
    # 3. Read or Summarize Thread
    if "summarize email thread" in t or "summarize this thread" in t:
        return ("summarize_thread", {"query": text})
        
    # 4. Search, Read, or Check Emails
    email_search_triggers = [
        "search email", "search emails", "find email", "find emails", "check email",
        "check emails", "unread emails", "unread messages", "unread mail", "inbox", "emails from", "emails about",
        "latest email", "read email", "read emails", "my email", "my emails",
        "emails of today", "emails today", "get email", "get emails",
        "show email", "show emails", "scan inbox", "scan email", "check my mail",
        "read my mail", "read my mails", "check my mails", "show my mails",
        "summarize my emails", "summarize emails", "summarize my mail", "summarize my mails",
        "recent mails", "recent emails", "latest mails", "latest emails", "recent mail"
    ]
    has_email_word = any(w in t for w in ["email", "emails", "gmail", "inbox", "mail", "mails"])
    has_read_action = any(w in t for w in ["read", "check", "search", "find", "get", "show", "summarize", "list", "open", "look", "today", "yesterday", "recent", "latest"])

    if any(k in t for k in email_search_triggers) or (has_email_word and has_read_action):
        max_results = 5
        count_match = re.search(r'\b(\d+)\s*(?:most\s+recent\s+|recent\s+|latest\s+)?(?:mails?|emails?|messages?)\b', t)
        if not count_match:
            count_match = re.search(r'(?:recent|latest|top|last)\s+(\d+)\s*(?:mails?|emails?|messages?)?', t)
        if count_match:
            try:
                c = int(count_match.group(1))
                if 1 <= c <= 20:
                    max_results = c
            except Exception:
                pass

        if "unread" in t:
            return ("search_emails", {"query": "is:unread", "max_results": max_results})
        if "today" in t:
            return ("search_emails", {"query": "newer_than:1d", "max_results": max_results})
        if "yesterday" in t:
            return ("search_emails", {"query": "newer_than:2d", "max_results": max_results})
        if "starred" in t:
            return ("search_emails", {"query": "is:starred", "max_results": max_results})
        if "important" in t:
            return ("search_emails", {"query": "is:important", "max_results": max_results})

        from_match = re.search(r'(?:from|by)\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+|[a-zA-Z0-9_-]+(?:\s+[a-zA-Z0-9_-]+)?)', text, re.IGNORECASE)
        if from_match:
            sender = from_match.group(1).strip()
            if sender.lower() not in ["my", "the", "inbox", "gmail", "email", "mail", "today", "yesterday", "recent", "plz", "please"]:
                return ("search_emails", {"query": f"from:{sender}", "max_results": max_results})

        for prefix in [
            "search email for", "search emails for", "search my email for", "search my emails for",
            "search mail for", "search mails for", "search for emails about", "search for email about",
            "find email from", "find emails from", "find emails about", "find email about",
            "check emails for", "check email for", "emails about", "email about", "mails about", "mail about",
            "emails regarding", "email regarding", "mails regarding", "mail regarding"
        ]:
            if prefix in t:
                idx = t.find(prefix) + len(prefix)
                sub_q = text[idx:].strip()
                sub_q = re.sub(r'[\?\.!]+$', '', sub_q).strip()
                sub_q = re.sub(r'\b(?:plz|please|thanks|thank you)\b', '', sub_q, flags=re.IGNORECASE).strip()
                if sub_q:
                    return ("search_emails", {"query": sub_q, "max_results": max_results})

        cleaned_topic = text
        noise_words = [
            r'\b(?:please|plz|can you|could you|would you|kindly|hey|hi|hello)\b',
            r'\b(?:read|check|search|find|get|show|summarize|list|open|fetch|scan|give me|see)\b',
            r'\b(?:my|the|any|all|some|these|those)\b',
            r'\b(?:\d+)\b',
            r'\b(?:most\s+recent|recent|latest|new|newest|last|top|first)\b',
            r'\b(?:mails?|emails?|messages?|inbox|gmail)\b',
            r'\b(?:and|to|for|about|regarding|of|them|me|us)\b',
            r'\b(?:summary|summarize)\b',
        ]
        for nw in noise_words:
            cleaned_topic = re.sub(nw, ' ', cleaned_topic, flags=re.IGNORECASE)
        cleaned_topic = re.sub(r'[^\w\s]', '', cleaned_topic).strip()

        if not cleaned_topic or len(cleaned_topic) <= 2:
            return ("search_emails", {"query": "", "max_results": max_results})
        
        return ("search_emails", {"query": cleaned_topic, "max_results": max_results})
        
    return None

def detect_calendar_intent(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Detects if query targets Google Calendar: connect, access check, list, availability, schedule, or delete."""
    t = text.lower().strip()

    # 0a. Check Calendar Access / Connection Status
    cal_access_triggers = [
        "access to my calendar", "access to calendar", "access to google calendar",
        "access to my calender", "access to calender", "access to google calender",
        "can you see my calendar", "can you see my calender", "can you access my calendar",
        "can you access my calender", "is my calendar connected", "is my calender connected",
        "do you have access to my calendar", "have access to my calendar",
        "do you have access to my calender", "have access to my calender"
    ]
    has_cal_kw = any(w in t for w in ["calendar", "calender", "schedule", "meeting", "meetings", "events", "agenda"])
    if any(trig in t for trig in cal_access_triggers) and has_cal_kw:
        return ("check_access", {"prompt": text})
    
    # 0. Connect / Authorize Calendar
    calendar_connect_triggers = [
        "connect calendar", "connect to calendar", "connect google calendar",
        "connect calender", "connect to calender", "connect google calender",
        "link calendar", "link calender", "sign in to calendar", "link google calendar"
    ]
    if any(k in t for k in calendar_connect_triggers):
        return ("connect_calendar", {})
    
    # 1. Schedule / Add Event (sensitive action -> proposal)
    schedule_triggers = [
        "schedule a meeting", "schedule meeting", "schedule event", "create calendar event",
        "add to my calendar", "book a meeting", "schedule a call", "set up a meeting",
        "add on my calendar", "add in my calendar", "add to calendar", "add to calender",
        "add on my calender", "add in my calender", "add a note on my calendar",
        "add an note on my calendar", "add a note on my calender", "add an note on my calender",
        "add note on my calendar", "add note on my calender", "put on my calendar", "put in my calendar",
        "put on my calender", "put in my calender", "mark on my calendar", "mark in my calendar",
        "block time on my calendar", "block time on my calender", "block time",
        "create event", "create an event", "create meeting", "schedule a discussion"
    ]
    has_schedule_action = any(w in t for w in ["add", "schedule", "book", "create", "set", "put", "mark", "block", "note"])
    has_cal_explicit = any(w in t for w in ["calendar", "calender", "meeting", "agenda", "appointment"])

    if any(k in t for k in schedule_triggers) or (has_schedule_action and has_cal_explicit):
        return ("create_event", {"prompt": text})
        
    # 2. Delete / Cancel Event (sensitive action -> proposal)
    if "cancel meeting" in t or "delete event" in t or "delete calendar event" in t or "remove meeting" in t or "cancel event" in t:
        return ("delete_event", {"prompt": text})
        
    # 3. Check Availability / Free slots
    avail_triggers = [
        "free slot", "free slots", "check availability", "am i free", "find a slot",
        "find 30-minute slot", "free time", "available slot", "available time",
        "minute slot", "free meeting", "open slot", "open slots", "availability for"
    ]
    if any(k in t for k in avail_triggers):
        return ("check_availability", {"prompt": text})
        
    # 4. List Calendar Events
    list_triggers = [
        "meetings do i have", "my meetings", "calendar for today", "calendar tomorrow",
        "what's on my calendar", "whats on my calendar", "upcoming meetings", "upcoming events",
        "schedule for tomorrow", "schedule for today", "my schedule", "events today",
        "what is on my calendar", "what's on my calender", "whats on my calender"
    ]
    has_cal_word = any(w in t for w in ["calendar", "calender", "meeting", "meetings", "event", "events", "schedule", "appointment"])
    has_cal_action = any(w in t for w in ["check", "what", "find", "show", "list", "have", "am i", "tomorrow", "today", "friday", "next", "upcoming", "view"])

    if any(k in t for k in list_triggers) or (has_cal_word and has_cal_action):
        return ("list_events", {"prompt": text})
        
    return None

def detect_task_intent(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Detects if query targets Task & Reminder Manager."""
    t = text.lower().strip()
    
    # 1. Complete Task
    if "complete task" in t or "finish task" in t or "mark task done" in t or "done with task" in t or "as completed" in t or "as complete" in t or "mark task" in t:
        return ("complete_task", {"prompt": text})
        
    # 2. List Tasks / Overdue
    if "overdue task" in t or "overdue tasks" in t:
        return ("list_overdue", {})
        
    list_triggers = [
        "my tasks", "list tasks", "show tasks", "what are my tasks", "view tasks",
        "todo list", "to-do list", "my to-dos", "pending tasks"
    ]
    if any(k in t for k in list_triggers):
        return ("list_tasks", {})
        
    # 3. Create Task
    create_triggers = [
        "create a task", "create task", "add a task", "add task", "new task",
        "remind me to", "add to my to-do", "add to-do", "add a to-do", "add a todo", "add todo", "todo:"
    ]
    if any(k in t for k in create_triggers):
        # Extract title
        title = text
        for prefix in ["create a task to", "create task to", "add a task to", "remind me to", "add task"]:
            if prefix in t:
                idx = t.find(prefix) + len(prefix)
                title = text[idx:].strip()
                break
        return ("create_task", {"title": title})
        
    return None

def detect_memory_intent(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Detects if user wants to save or view persistent preferences/memories."""
    t = text.lower().strip()
    
    if "remember that" in t or "save to memory that" in t or "keep in mind that" in t:
        for prefix in ["remember that", "save to memory that", "keep in mind that"]:
            if prefix in t:
                idx = t.find(prefix) + len(prefix)
                content = text[idx:].strip()
                return ("add_memory", {"content": content})
                
    if "what do you remember" in t or "my saved preferences" in t or "list memories" in t or "show memories" in t:
        return ("list_memories", {})
        
    return None

def detect_multi_intent(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Detects multi-step compound queries requiring multi-tool orchestration."""
    t = text.lower().strip()
    has_email = any(k in t for k in ["email", "mail", "gmail", "inbox", "message from", "thread"])
    has_meeting = any(k in t for k in ["meeting", "schedule", "calendar", "invite", "call", "appointment"])
    has_task = any(k in t for k in ["task", "todo", "to-do", "reminder"])
    
    if has_email and has_meeting:
        return ("email_and_calendar", {"prompt": text})
    if has_email and has_task and any(k in t for k in ["create", "add", "make", "save", "put in"]):
        return ("email_and_task", {"prompt": text})
    return None

