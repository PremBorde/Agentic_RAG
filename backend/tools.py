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
        "top 5 news", "top 10 news", "news headlines", "headlines today"
    ]
    if any(trig in t for trig in triggers):
        return True
    if re.search(r'\b(?:web\s*search|search\s*(?:the\s+)?(?:web|internet|online))\b', t):
        return True
    if re.search(r'\b(?:today(?:\x27s)?|current|latest|breaking|recent|top\s*\d*)\s+(?:\w+\s+)?news\b', t) or re.search(r'\b(?:tech|world|market|crypto|ai|space|finance|sports)\s+news\b', t):
        return True
    if re.search(r'\bnews\s+(?:today|headlines)\b', t):
        return True
    if re.search(r'\b(?:weather\s+in|stock\s+price|current\s+price\s+of)\b', t):
        return True
    return False

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
        "check emails", "unread emails", "inbox", "emails from", "emails about",
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
        "find 30-minute slot", "free time", "available slot", "available time"
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

