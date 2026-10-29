import re
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
    """Detects greetings, pleasantries, small talk, and questions about bot capabilities."""
    if not text:
        return True
    
    # Strip non-alphanumeric punctuation to handle "Hello! What can you do?", "Hi...", "Hey!!"
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', text).lower().strip()
    words = cleaned.split()
    if not words:
        return True

    conversational_starters = [
        "hi", "hello", "hey", "greetings", "howdy", "hola", "yo", "sup", "namaste",
        "good morning", "good afternoon", "good evening", "good night", "good day",
        "how are you", "what's up", "whats up", "how do you do",
        "who are you", "what are you", "what can you do", "what do you do",
        "tell me about yourself", "how can you help", "who made you", "what is this app",
        "thanks", "thank you", "thx", "ty", "many thanks", "appreciate it",
        "bye", "goodbye", "see you", "cya", "take care",
        "ok", "okay", "cool", "great", "awesome", "nice", "got it", "sure"
    ]
    
    for starter in conversational_starters:
        if cleaned.startswith(starter):
            return True
            
    first_two = " ".join(words[:2])
    first_three = " ".join(words[:3])
    first_four = " ".join(words[:4])
    for starter in conversational_starters:
        if starter in (first_two, first_three, first_four):
            return True

    return any(re.match(p, cleaned) for p in GREETING_PATTERNS)

def is_explicit_web_search(text: str) -> bool:
    """Detects if the user explicitly requested live internet / web search."""
    t = text.lower().strip()
    triggers = [
        "search the web", "search online", "search web", "browse the web",
        "google", "duckduckgo", "latest news", "today's news", "live search",
        "current price", "stock price", "news today", "latest updates on",
        "who won the", "recent news", "trending today"
    ]
    return any(trig in t for trig in triggers)

def is_followup_query(text: str) -> bool:
    """Detects commands or short follow-up questions that refer to the previous topic/document."""
    t = text.lower().strip()
    followup_starters = [
        "list", "give", "summarize", "summary", "explain", "tell me", "what about",
        "why", "how", "what else", "more", "details", "points", "key",
        "can you", "show me", "continue", "elaborate", "bullet", "bullets", "outline"
    ]
    words = t.split()
    return len(words) <= 7 or any(t.startswith(s) for s in followup_starters)
