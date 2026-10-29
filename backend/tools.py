import re
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
    """Detects greetings, pleasantries, small talk, and questions about bot capabilities."""
    if not text:
        return True
    
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

def detect_gmail_intent(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Detects if query targets Gmail: search, read, draft, or send."""
    t = text.lower().strip()
    
    # 1. Send Email proposal (sensitive action -> proposal)
    if "send an email" in t or "send email" in t or "shoot an email" in t or "send a mail" in t:
        # Extract basic parameters
        to_match = re.search(r"to\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", text, re.IGNORECASE)
        to_email = to_match.group(1) if to_match else "recipient@example.com"
        
        subj_match = re.search(r"subject\s+['\"]?([^'\"\n]+)['\"]?", text, re.IGNORECASE)
        subj = subj_match.group(1).strip() if subj_match else "Project Update"
        
        # Body extraction or placeholder
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
        "check emails", "unread emails", "inbox", "emails from", "emails about",
        "latest email", "read email", "read emails", "my email", "my emails",
        "emails of today", "emails today", "get email", "get emails",
        "show email", "show emails", "scan inbox", "scan email", "check my mail"
    ]
    has_email_word = any(w in t for w in ["email", "emails", "gmail", "inbox", "mail"])
    has_read_action = any(w in t for w in ["read", "check", "search", "find", "get", "show", "summarize", "list", "open", "look", "today", "yesterday", "recent", "latest"])

    if any(k in t for k in email_search_triggers) or (has_email_word and has_read_action):
        # Extract search query
        q = text
        for prefix in ["search email for", "search emails for", "find email from", "find emails about", "check emails for", "search email about", "read my emails of", "read emails of", "read my emails"]:
            if prefix in t:
                idx = t.find(prefix) + len(prefix)
                q = text[idx:].strip()
                break
        return ("search_emails", {"query": q})
        
    return None

def detect_calendar_intent(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Detects if query targets Google Calendar: list, availability, schedule, or delete."""
    t = text.lower().strip()
    
    # 1. Schedule Event (sensitive action -> proposal)
    schedule_triggers = [
        "schedule a meeting", "schedule meeting", "schedule event", "create calendar event",
        "add to my calendar", "book a meeting", "schedule a call", "set up a meeting"
    ]
    if any(k in t for k in schedule_triggers):
        return ("create_event", {"prompt": text})
        
    # 2. Delete / Cancel Event (sensitive action -> proposal)
    if "cancel meeting" in t or "delete event" in t or "delete calendar event" in t or "remove meeting" in t:
        return ("delete_event", {"prompt": text})
        
    # 3. Check Availability / Free slots
    avail_triggers = [
        "free slot", "free slots", "check availability", "am i free", "find a slot",
        "find 30-minute slot", "free time", "available slot", "available time"
    ]
    if any(k in t for k in avail_triggers):
        return ("check_availability", {"prompt": text})
        
    # 4. List Calendar Events
    list_triggers = [
        "meetings do i have", "my meetings", "calendar for today", "calendar tomorrow",
        "what's on my calendar", "whats on my calendar", "upcoming meetings", "upcoming events",
        "schedule for tomorrow", "schedule for today", "my schedule"
    ]
    has_cal_word = any(w in t for w in ["calendar", "meeting", "meetings", "event", "events", "schedule", "appointment"])
    has_cal_action = any(w in t for w in ["check", "what", "find", "show", "list", "have", "am i", "tomorrow", "today", "friday", "next", "upcoming", "view"])

    if any(k in t for k in list_triggers) or (has_cal_word and has_cal_action):
        return ("list_events", {"prompt": text})
        
    return None

def detect_task_intent(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Detects if query targets Task & Reminder Manager."""
    t = text.lower().strip()
    
    # 1. Complete Task
    if "complete task" in t or "finish task" in t or "mark task done" in t or "done with task" in t:
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
        "remind me to", "add to my to-do", "add to-do", "todo:"
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
