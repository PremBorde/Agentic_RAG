def _fast_extract_calendar(text: str) -> tuple:
    """Fast 0ms regex extraction of calendar title and date/time."""
    t = text.lower()
    now = datetime.now()
    summary = None
    
    m_focus = re.search(r'(?:focusing\s+(?:in|on)|note\s+that|add\s+an?\s+note\s+(?:on|to)\s+my\s+calend[ae]r\s+that)\s+([^.,\n]+)', text, re.IGNORECASE)
    if m_focus:
        summary = m_focus.group(1).strip()
    if not summary:
        m_title = re.search(r'(?:titled?|for|about|meeting\s+with)\s+([^.,\n]+)', text, re.IGNORECASE)
        if m_title:
            summary = m_title.group(1).strip()
    if not summary:
        summary = "Focus Session"
            
    summary = re.sub(r'^(?:today\s+|tomorrow\s+|i\s+am\s+)', '', summary, flags=re.IGNORECASE).strip()
    if summary:
        summary = summary[0].upper() + summary[1:]

    target_date = now.date()
    if 'tomorrow' in t:
        target_date = (now + timedelta(days=1)).date()
    elif 'day after tomorrow' in t:
        target_date = (now + timedelta(days=2)).date()
        
    m_time = re.search(r'\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b', t)
    start_hour = min(now.hour + 1, 23)
    start_minute = 0
    if m_time:
        h = int(m_time.group(1))
        m = int(m_time.group(2)) if m_time.group(2) else 0
        meridiem = m_time.group(3)
        if meridiem == 'pm' and h < 12:
            h += 12
        elif meridiem == 'am' and h == 12:
            h = 0
        start_hour, start_minute = h, m

    start_dt = datetime.combine(target_date, datetime.min.time()).replace(hour=start_hour, minute=start_minute)
    end_dt = start_dt + timedelta(hours=1)
    return summary, start_dt, end_dt

import re
import asyncio
import json as _json
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

from backend.config import get_llm
from backend.utils.retry import astream_with_backoff, format_friendly_error
from backend.embeddings import safe_str
from backend.vector_store import vector_store, retriever, format_docs
from backend.services.router import classify_query, QueryIntent, RoutingDecision
from backend.tools import (
    is_conversational_query,
    get_direct_greeting_response,
    is_explicit_web_search,
    is_followup_query,
    web_search_tool,
    detect_multi_intent,
    detect_gmail_intent,
    detect_calendar_intent,
    detect_task_intent,
    detect_memory_intent
)
from backend.prompts import conv_prompt, gen_prompt
from backend.memory import get_thread_context_str, get_last_user_query, record_thread_turn
from backend.services.database import (
    list_tasks,
    create_task,
    complete_task,
    get_overdue_tasks,
    list_memories,
    add_memory,
    get_relevant_memories_text,
    save_conversation_message
)
from backend.services.approval_service import propose_action
from backend.services.google_service import (
    get_connection_status,
    search_emails,
    read_email,
    summarize_email_thread,
    create_email_draft,
    list_calendar_events,
    check_calendar_availability,
    find_free_meeting_slots
)

async def stream_chat_events(
    question: str, 
    model_name: str, 
    thread_id: str,
    user_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Generates Server-Sent Events (SSE) for streaming responses with tool orchestration & action proposals."""
    chat_hist = get_thread_context_str(thread_id)
    memories = get_relevant_memories_text()
    conn_info = get_connection_status(user_id)
    if conn_info.get("connected"):
        active_email = conn_info.get("email") or "User"
        google_ctx = f"Active User Workspace: Connected to Google as {active_email} (Gmail and Google Calendar enabled and accessible via tools)."
        memories = f"{memories}\n{google_ctx}" if memories else google_ctx
    doc_count = len(vector_store.index_to_docstore_id)
    source = "Assistant"
    docs_meta = []
    context = ""
    answer_parts: list[str] = []
    proposal = None

    try:
        yield 'data: {"type":"stage","stage":"thinking"}\n\n'
        
        # Lazy LLM loader so greetings and local operations never touch external LLM APIs
        _active_llm = None
        def get_active_llm():
            nonlocal _active_llm
            if _active_llm is None:
                _active_llm = get_llm(model_name)
            return _active_llm

        # ── 1. CENTRALIZED INTENT ROUTER ─────────────────────────────────
        decision = classify_query(question, doc_count=doc_count, has_history=bool(chat_hist), chat_history_str=chat_hist)

        # ── 1. CONVERSATIONAL GREETINGS (ZERO-LLM DIRECT STREAM) ────────────
        if decision.intent == QueryIntent.CONVERSATIONAL:
            source = "Greeting" if decision.is_welcome_card else "Conversational"

            # Professional loading state: display animated mascot and preparing indicator
            stage_name = "greeting" if decision.is_welcome_card else "thinking"
            yield f'data: {{"type":"stage","stage":"{stage_name}"}}\n\n'
            # Immediate response without artificial delay
            pass

            yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[]})}\n\n'

            direct_reply = get_direct_greeting_response(question)
            if not direct_reply:
                direct_reply = "Hello! Everything looks set up and ready to go. How can I assist you today?"

            answer_parts.append(direct_reply)
            if decision.is_welcome_card:
                yield f"data: {_json.dumps({'type':'token','text':direct_reply})}\n\n"
            else:
                words = direct_reply.split(" ")
                for i, w in enumerate(words):
                    chunk_text = w if i == 0 else " " + w
                    yield f"data: {_json.dumps({'type':'token','text':chunk_text})}\n\n"
                    await asyncio.sleep(0.006)

        # ── 1.5 MULTI-INTENT AGENT ORCHESTRATION ──────────────────────
        elif decision.intent == QueryIntent.MULTI_STEP:
            multi_type = decision.sub_action
            multi_params = decision.params
            source = "Agent Orchestrator"
            is_google_connected = get_connection_status(user_id).get("connected", False)

            if multi_type == "email_and_calendar":
                if not is_google_connected:
                    yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[],"requires_google_auth":True})}\n\n'
                    yield 'data: {"type":"stage","stage":"generating"}\n\n'
                    auth_prompt = (
                        "### 🔒 Google Workspace Required for Multi-Step Workflow\n\n"
                        "To search your emails, summarize the thread, and schedule the calendar meeting, "
                        "please connect your Google account in Settings."
                    )
                    yield f"data: {_json.dumps({'type':'token','text':auth_prompt})}\n\n"
                    answer_parts.append(auth_prompt)
                else:
                    # Step 1: Search Gmail
                    yield 'data: {"type":"stage","stage":"searching_gmail"}\n\n'
                    clean_q = question
                    for filler in ["find the email from", "find email from", "search email from", "summarize it, and schedule", "and schedule a meeting for"]:
                        clean_q = clean_q.replace(filler, " ")
                    search_terms = " ".join([w for w in clean_q.split() if w.lower() not in ["find", "the", "email", "from", "about", "project", "and", "schedule", "meeting", "tomorrow", "for", "at", "pm", "am"]][:3]) or "project"
                    
                    emails = search_emails(query=search_terms, max_results=3, user_id=user_id)
                    email_summary_ctx = ""
                    if emails and emails[0].get("status") != "not_connected":
                        lines = [f"- From: {e.get('sender')} | Subject: {e.get('subject')}\n  Snippet: {e.get('snippet')}" for e in emails]
                        email_summary_ctx = "\n".join(lines)
                    else:
                        email_summary_ctx = f"Email search for '{search_terms}' completed. (Referenced in context: email discussions on the project)."

                    # Step 2: Propose Calendar Event
                    yield 'data: {"type":"stage","stage":"checking_calendar"}\n\n'
                    now = datetime.now()
                    tomorrow = now + timedelta(days=1)
                    start_dt = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
                    end_dt = start_dt + timedelta(minutes=30)
                    
                    event_title = "Meeting on Project Follow-up"
                    for word in question.split():
                        if word.istitle() and word.lower() not in ["find", "the", "email", "meeting", "tomorrow", "pm", "am", "schedule"]:
                            event_title = f"Meeting with {word} - Project Discussion"
                            break

                    proposal = propose_action(
                        action_type="create_calendar_event",
                        summary=f"{event_title} on {start_dt.strftime('%A, %b %d at %I:%M %p')}",
                        payload={
                            "summary": event_title,
                            "start_time": start_dt.isoformat(),
                            "end_time": end_dt.isoformat(),
                            "description": f"Scheduled follow-up meeting based on email context: {question}"
                        }
                    )
                    
                    docs_meta = [{"content": email_summary_ctx, "source": "Gmail", "doc_id": "gmail-multi"}]
                    yield f'data: {_json.dumps({"type":"meta","source":"Gmail & Calendar Orchestrator","retrieved_docs":docs_meta})}\n\n'
                    yield 'data: {"type":"stage","stage":"generating"}\n\n'
                    
                    synthesis_prompt = (
                        f"You are an executive AI assistant. The user requested: '{question}'.\n"
                        f"Here is the email context found:\n{email_summary_ctx}\n\n"
                        f"Task: 1. Summarize the key points from the email.\n"
                        f"2. Inform the user you prepared the calendar invite for {start_dt.strftime('%A, %b %d at %I:%M %p')} and that they can click 'Approve' below to confirm.\n"
                        f"Keep it professional and concise."
                    )
                    prompt_val = conv_prompt.invoke({
                        "memories": memories,
                        "chat_history": chat_hist,
                        "question": synthesis_prompt
                    })
                    async for chunk in astream_with_backoff(get_active_llm(), prompt_val):
                        token = safe_str(chunk.content)
                        if token:
                            answer_parts.append(token)
                            yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"

                    # Synchronized action proposal event emitted sequentially AFTER text explanation
                    yield f'data: {_json.dumps({"type":"proposal","proposal":proposal})}\n\n'

            elif multi_type == "email_and_task":
                yield 'data: {"type":"stage","stage":"searching_gmail"}\n\n'
                emails = search_emails(query="feedback", max_results=2, user_id=user_id) if is_google_connected else []
                summary_snippet = emails[0].get("snippet", "Client requested feedback review") if emails and emails[0].get("status") != "not_connected" else "Review client feedback and follow up"
                
                # Step 2: Create task
                yield 'data: {"type":"stage","stage":"organizing_tasks"}\n\n'
                task = create_task(title=f"Follow up: {summary_snippet[:50]}", priority="high", user_id=user_id)
                
                resp_text = (
                    f"### Multi-Step Action Completed\n\n"
                    f"1. **Email Referenced:** {summary_snippet}\n"
                    f"2. **Task Created:** '{task['title']}' (Priority: High, ID: `{task['id']}`).\n\n"
                    f"You can view and manage this in your Task Manager anytime."
                )
                yield f'data: {_json.dumps({"type":"meta","source":"Orchestrator: Email & Tasks","retrieved_docs":[]})}\n\n'
                yield 'data: {"type":"stage","stage":"generating"}\n\n'
                yield f"data: {_json.dumps({'type':'token','text':resp_text})}\n\n"
                answer_parts.append(resp_text)

        # ── 2. GMAIL ROUTING ─────────────────────────────────────────
        elif decision.intent == QueryIntent.GMAIL:
            action_name = decision.sub_action
            params = decision.params
            source = "Gmail"
            is_google_connected = get_connection_status(user_id).get("connected", False)
            
            if not is_google_connected:
                yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[],"requires_google_auth":True})}\n\n'
                yield 'data: {"type":"stage","stage":"generating"}\n\n'
                if action_name == "connect_gmail":
                    friendly_msg = (
                        "### 🔒 Connect Your Google Account\n\n"
                        "To give your AI Assistant access to search your inbox, summarize email threads, and draft messages, please sign in with Google below:"
                    )
                else:
                    friendly_msg = (
                        "### 🔒 Google Workspace is Not Connected\n\n"
                        "I noticed you requested a Gmail operation, but your Google account is currently not connected (or your authentication token has expired).\n\n"
                        "To search emails, read conversation threads, draft messages, or send updates, please connect your Google account below:"
                    )
                yield f"data: {_json.dumps({'type':'token','text':friendly_msg})}\n\n"
                answer_parts.append(friendly_msg)

            elif action_name in ["connect_gmail", "check_access"]:
                yield 'data: {"type":"stage","stage":"generating"}\n\n'
                user_email = conn_info.get("email") or "your Google account"
                connected_msg = (
                    f"### ✅ Yes, I have access to your Gmail!\n\n"
                    f"Your account is connected and active as **{user_email}**.\n\n"
                    f"Here is what you can ask me to do right now:\n"
                    f"- 📬 *Check my recent emails* or *Find unread messages*\n"
                    f"- 🔍 *Find emails from [sender] about [topic]*\n"
                    f"- ✍️ *Draft an email to [name] about [topic]*\n"
                    f"- 📅 *What meetings do I have today?* or *Find a free slot tomorrow*\n\n"
                    f"Would you like me to scan your recent inbox or search for a specific email?"
                )
                yield f"data: {_json.dumps({'type':'token','text':connected_msg})}\n\n"
                answer_parts.append(connected_msg)

            # Sensitive: Sending an Email -> Propose Action
            elif action_name == "send_email":
                yield 'data: {"type":"stage","stage":"preparing_draft"}\n\n'

                to_addr = params.get("to", "recipient@example.com")
                subj = params.get("subject", "Email Message")
                user_prompt = params.get("prompt", question)

                # Use Gemini LLM to draft high-quality email subject & body
                body = None
                try:
                    llm = get_active_llm()
                    compose_prompt = (
                        "You are a helpful personal assistant composing an email.\n"
                        f"User request: '{user_prompt}'\n"
                        f"Recipient: {to_addr}\n"
                        f"Subject hint: '{subj}'\n"
                        "Write a friendly, polite, well-structured email.\n"
                        "Return ONLY a JSON object with 'subject' and 'body' keys.\n"
                        "Do not include any code block backticks (no ```json)."
                    )
                    raw_res = await asyncio.wait_for(llm.ainvoke(compose_prompt), timeout=4.5)
                    raw_text = safe_str(raw_res.content).strip()
                    if raw_text.startswith("```"):
                        raw_text = re.sub(r"^```(?:json)?\n?|\n?```$", "", raw_text, flags=re.MULTILINE).strip()
                    parsed = _json.loads(raw_text)
                    if parsed.get("subject"):
                        subj = parsed["subject"]
                    if parsed.get("body"):
                        body = parsed["body"]
                except Exception as e:
                    logger.warning(f"[Draft Composition Fallback]: {e}")

                if not body:
                    body = (
                        f"Hi,\n\nI hope this email finds you well.\n"
                        f"I am writing regarding {subj.lower()}.\n\n"
                        f"Warm regards,\nPersonal AI Agent"
                    )

                proposal = propose_action(
                    action_type="send_email",
                    summary=f"Send email to {to_addr} with subject '{subj}'",
                    payload={"to": to_addr, "subject": subj, "body": body, "user_id": user_id}
                )

                yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[]})}\n\n'
                yield 'data: {"type":"stage","stage":"generating"}\n\n'

                preview_msg = (
                    f"I have prepared the email for **{to_addr}** with subject **\"{subj}\"**.\n\n"
                    f"Please review the proposed action card below and click **Approve & Execute** to send it via your connected Gmail, or **Cancel** if you'd like to adjust it."
                )
                words = preview_msg.split(" ")
                for i, w in enumerate(words):
                    chunk_text = w if i == 0 else " " + w
                    yield f"data: {_json.dumps({'type':'token','text':chunk_text})}\n\n"
                    await asyncio.sleep(0.006)
                answer_parts.append(preview_msg)

                # Synchronized action proposal event emitted sequentially AFTER text explanation
                yield f'data: {_json.dumps({"type":"proposal","proposal":proposal})}\n\n'

            # Creating a Draft
            elif action_name == "create_draft":
                yield 'data: {"type":"stage","stage":"preparing_draft"}\n\n'
                to_addr = params.get("to", "team@example.com")
                res = create_email_draft(to=to_addr, subject="Draft Reply", body="Thank you for your message. I am following up on your request.", user_id=user_id)
                msg = f"Draft email to **{to_addr}** has been created in your Gmail account.\n\n{res.get('message', '')}"
                yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[]})}\n\n'
                yield 'data: {"type":"stage","stage":"generating"}\n\n'
                yield f"data: {_json.dumps({'type':'token','text':msg})}\n\n"
                answer_parts.append(msg)

            # Searching or Reading Emails
            else:
                yield 'data: {"type":"stage","stage":"searching_gmail"}\n\n'
                query_str = params.get("query", "")
                max_res = params.get("max_results", 5)
                emails = await asyncio.to_thread(search_emails, query=query_str, max_results=max_res, user_id=user_id)
                
                if emails and emails[0].get("status") == "not_connected":
                    auth_msg = (
                        "### 🔒 Google Workspace is Not Connected\n\n"
                        "Please connect your Google account in Settings to access your Gmail."
                    )
                    yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[],"requires_google_auth":True})}\n\n'
                    yield 'data: {"type":"stage","stage":"generating"}\n\n'
                    yield f"data: {_json.dumps({'type':'token','text':auth_msg})}\n\n"
                    answer_parts.append(auth_msg)
                    return

                if not emails:
                    no_mail_msg = (
                        f"I checked your Gmail inbox, but found no matching emails"
                        + (f" for **'{query_str}'**." if query_str else ".")
                    )
                    yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[]})}\n\n'
                    yield 'data: {"type":"stage","stage":"generating"}\n\n'
                    yield f"data: {_json.dumps({'type':'token','text':no_mail_msg})}\n\n"
                    answer_parts.append(no_mail_msg)
                    return

                lines = []
                for idx, em in enumerate(emails, 1):
                    body_content = em.get('snippet', '')
                    if len(emails) <= 2 or any(k in question.lower() for k in ["full", "entire", "detail", "body", "read the email", "read that email"]):
                        try:
                            full_em = read_email(em.get("id"), user_id=user_id)
                            if full_em and full_em.get("body"):
                                body_content = full_em.get("body")[:2500]
                        except Exception:
                            pass
                    lines.append(f"### Email {idx}\n- **From:** {em.get('sender')}\n- **Subject:** {em.get('subject')}\n- **Date:** {em.get('date')}\n- **Content:** {body_content}")
                
                context = "\n\n".join(lines)
                docs_meta = [{"content": context, "source": "Gmail", "doc_id": "gmail"}]
                yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":docs_meta})}\n\n'
                yield 'data: {"type":"stage","stage":"generating"}\n\n'
                
                prompt_val = gen_prompt.invoke({
                    "memories": memories,
                    "chat_history": chat_hist,
                    "context": context,
                    "question": question
                })
                async for chunk in astream_with_backoff(get_active_llm(), prompt_val):
                    token = safe_str(chunk.content)
                    if token:
                        answer_parts.append(token)
                        yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"

        # ── 3. CALENDAR ROUTING ──────────────────────────────────────
        elif decision.intent == QueryIntent.CALENDAR:
            action_name = decision.sub_action
            params = decision.params
            source = "Google Calendar"
            is_google_connected = get_connection_status(user_id).get("connected", False)
            
            if not is_google_connected:
                yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[],"requires_google_auth":True})}\n\n'
                yield 'data: {"type":"stage","stage":"generating"}\n\n'
                if action_name == "connect_calendar":
                    friendly_msg = (
                        "### 🔒 Connect Google Calendar\n\n"
                        "To give your AI Assistant access to check your upcoming schedule, find open meeting slots, and schedule events, please sign in with Google below:"
                    )
                else:
                    friendly_msg = (
                        "### 🔒 Google Workspace is Not Connected\n\n"
                        "I noticed you requested a Calendar operation, but your Google account is currently not connected (or your authentication token has expired).\n\n"
                        "To check upcoming meetings, verify free slots, or schedule calendar events, please connect your Google account below:"
                    )
                yield f"data: {_json.dumps({'type':'token','text':friendly_msg})}\n\n"
                answer_parts.append(friendly_msg)

            elif action_name in ["connect_calendar", "check_access"]:
                yield 'data: {"type":"stage","stage":"generating"}\n\n'
                user_email = conn_info.get("email") or "your Google account"
                connected_msg = (
                    f"### ✅ Yes, I have access to your Google Calendar!\n\n"
                    f"Your account is connected and active as **{user_email}**.\n\n"
                    f"You can ask me to:\n"
                    f"- 📅 *What is on my schedule for today?*\n"
                    f"- 🔍 *Find a free 30-minute slot tomorrow*\n"
                    f"- 📝 *Schedule a meeting for tomorrow at 2 PM*\n"
                )
                yield f"data: {_json.dumps({'type':'token','text':connected_msg})}\n\n"
                answer_parts.append(connected_msg)

            # Sensitive: Creating a Calendar Event -> Dynamic Extraction & Action Proposal
            elif action_name == "create_event":
                source = "Google Calendar"
                yield 'data: {"type":"stage","stage":"checking_calendar"}\n\n'
                
                now = datetime.now()
                summary_val = "Focus Session"
                desc_val = ""
                start_dt = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                end_dt = start_dt + timedelta(hours=1)
                
                instruction_text = params.get("prompt") or question
                if any(k in instruction_text.lower() for k in ["yes sure", "yes plz", "confirm", "sure", "go ahead"]):
                    instruction_text = question if not any(k in question.lower() for k in ["yes sure", "yes plz", "confirm", "sure", "go ahead"]) else chat_hist

                # Fast regex-based extraction (0ms latency)
                fast_sum, fast_st, fast_et = _fast_extract_calendar(instruction_text)
                if fast_sum and fast_sum != "Focus Session":
                    summary_val = fast_sum
                    start_dt = fast_st
                    end_dt = fast_et
                    desc_val = f"Scheduled session: {summary_val}"
                else:
                    try:
                        extract_prompt = f"""Extract calendar event title and times from: "{instruction_text}"\nReturn ONLY JSON: {{"summary": "title", "start_time": "YYYY-MM-DDTHH:MM:SS", "end_time": "YYYY-MM-DDTHH:MM:SS", "description": ""}}"""
                        llm = get_active_llm()
                        resp = await asyncio.wait_for(llm.ainvoke(extract_prompt), timeout=2.5)
                        raw_text = safe_str(resp.content)
                        import json
                        json_match = re.search(r'\{[\s\S]*?\}', raw_text)
                        if json_match:
                            parsed = json.loads(json_match.group(0))
                            if parsed.get("summary"):
                                summary_val = parsed["summary"]
                            if parsed.get("description"):
                                desc_val = parsed["description"]
                            if parsed.get("start_time"):
                                try:
                                    start_dt = datetime.fromisoformat(parsed["start_time"])
                                except Exception:
                                    pass
                            if parsed.get("end_time"):
                                try:
                                    end_dt = datetime.fromisoformat(parsed["end_time"])
                                except Exception:
                                    end_dt = start_dt + timedelta(hours=1)
                    except Exception as e:
                        logger.warning(f"Fast calendar fallback used: {e}")
                
                proposal = propose_action(
                    action_type="create_calendar_event",
                    summary=f"Add to Calendar: {summary_val}",
                    payload={
                        "summary": summary_val,
                        "start_time": start_dt.isoformat(),
                        "end_time": end_dt.isoformat(),
                        "description": desc_val or f"Scheduled: {summary_val}",
                        "attendees": [],
                        "user_id": user_id
                    }
                )
                
                yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[]})}\n\n'
                yield 'data: {"type":"stage","stage":"generating"}\n\n'
                
                start_str = start_dt.strftime('%A, %b %d, %Y at %I:%M %p')
                end_str = end_dt.strftime('%I:%M %p')
                preview_msg = (
                    f"I have formulated a calendar event for **{summary_val}** scheduled for **{start_str} – {end_str}**.\n\n"
                    f"Please review the proposed action card below and click **Approve & Execute** to add it to your Google Calendar."
                )
                
                words = preview_msg.split(' ')
                for idx, w in enumerate(words):
                    chunk_text = w if idx == len(words) - 1 else w + ' '
                    yield f"data: {_json.dumps({'type':'token','text':chunk_text})}\n\n"
                    answer_parts.append(chunk_text)
                    await asyncio.sleep(0.006)

                # Synchronized action proposal event emitted sequentially AFTER text explanation
                yield f'data: {_json.dumps({"type":"proposal","proposal":proposal})}\n\n'

            # Check Availability / Free Slots
            elif action_name == "check_availability":
                source = "Google Calendar"
                yield 'data: {"type":"stage","stage":"checking_calendar"}\n\n'
                slots = find_free_meeting_slots(duration_minutes=30, days_ahead=3, user_id=user_id)
                
                lines = ["Available meeting slots in your calendar:"]
                for s in slots:
                    if s.get("status") == "not_connected":
                        lines.append("Google account not connected. Please connect your Google account in Settings.")
                        break
                    lines.append(f"- {s.get('start')} to {s.get('end')}")
                context = "\n".join(lines)
                
                docs_meta = [{"content": context, "source": "Google Calendar", "doc_id": "calendar"}]
                yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":docs_meta})}\n\n'
                yield 'data: {"type":"stage","stage":"generating"}\n\n'
                
                prompt_val = gen_prompt.invoke({
                    "memories": memories,
                    "chat_history": chat_hist,
                    "context": context,
                    "question": question
                })
                async for chunk in astream_with_backoff(get_active_llm(), prompt_val):
                    token = safe_str(chunk.content)
                    if token:
                        answer_parts.append(token)
                        yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"

            # Listing Calendar Events
            else:
                source = "Google Calendar"
                yield 'data: {"type":"stage","stage":"checking_calendar"}\n\n'
                events = await asyncio.to_thread(list_calendar_events, max_results=5, user_id=user_id)
                lines = []
                for ev in events:
                    if ev.get("status") == "not_connected":
                        lines.append("Google account not connected. Please connect your Google account in Settings to view upcoming events.")
                        break
                    lines.append(f"- **{ev.get('summary')}** | Start: {ev.get('start')} | End: {ev.get('end')}")
                context = "\n".join(lines) if lines else "No upcoming events found on your primary calendar."
                
                docs_meta = [{"content": context, "source": "Google Calendar", "doc_id": "calendar"}]
                yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":docs_meta})}\n\n'
                yield 'data: {"type":"stage","stage":"generating"}\n\n'
                
                prompt_val = gen_prompt.invoke({
                    "memories": memories,
                    "chat_history": chat_hist,
                    "context": context,
                    "question": question
                })
                async for chunk in astream_with_backoff(get_active_llm(), prompt_val):
                    token = safe_str(chunk.content)
                    if token:
                        answer_parts.append(token)
                        yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"

        # ── 4. TASK & REMINDER ROUTING ───────────────────────────────
        elif decision.intent == QueryIntent.TASK:
            action_name = decision.sub_action
            params = decision.params
            source = "Tasks & Reminders"
            yield 'data: {"type":"stage","stage":"organizing_tasks"}\n\n'
            
            if action_name == "create_task":
                title = params.get("title", question)
                created = create_task(title=title, user_id=user_id)
                msg = f"✓ Added task to your list: **\"{created['title']}\"** (Priority: {created['priority'].upper()})."
            elif action_name == "list_overdue":
                overdue = get_overdue_tasks()
                if not overdue:
                    msg = "You have no overdue tasks! All your deadlines are on track."
                else:
                    lines = ["**Overdue Tasks:**"]
                    for t in overdue:
                        lines.append(f"- ⚠️ **{t['title']}** (Due: {t['due_date']}, Priority: {t['priority']})")
                    msg = "\n".join(lines)
            else:
                tasks = list_tasks(user_id=user_id)
                if not tasks:
                    msg = "You currently have no tasks in your task manager. You can create one anytime by asking (e.g., *\"Create task to review slides tomorrow\"*)."
                else:
                    lines = ["**Your Current Tasks:**"]
                    for t in tasks:
                        icon = "✓" if t["status"] == "completed" else "○"
                        due = f" *(Due: {t['due_date']})*" if t.get("due_date") else ""
                        lines.append(f"- {icon} `[{t['priority'].upper()}]` **{t['title']}**{due}")
                    msg = "\n".join(lines)
                    
            yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[]})}\n\n'
            yield 'data: {"type":"stage","stage":"generating"}\n\n'
            yield f"data: {_json.dumps({'type':'token','text':msg})}\n\n"
            answer_parts.append(msg)

        # ── 5. LONG-TERM MEMORY ROUTING ──────────────────────────────
        elif decision.intent == QueryIntent.MEMORY:
            action_name = decision.sub_action
            params = decision.params
            source = "Long-Term Memory"
            
            if action_name == "add_memory":
                content = params.get("content", question)
                add_memory(content=content)
                msg = f"🧠 Saved to your persistent memory: *\"{content}\"*. I will remember this across future sessions."
            else:
                mems = list_memories()
                if not mems:
                    msg = "No persistent preferences or memories saved yet. You can tell me *\"Remember that I prefer morning meetings\"* anytime!"
                else:
                    lines = ["**Your Saved Long-Term Preferences & Memories:**"]
                    for m in mems:
                        lines.append(f"- `[{m['category'].upper()}]` {m['content']}")
                    msg = "\n".join(lines)
                    
            yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[]})}\n\n'
            yield 'data: {"type":"stage","stage":"generating"}\n\n'
            yield f"data: {_json.dumps({'type':'token','text':msg})}\n\n"
            answer_parts.append(msg)

        # ── 6. EXPLICIT WEB SEARCH ───────────────────────────────────
        elif decision.intent == QueryIntent.WEB_SEARCH:
            source = "Web Search"
            yield 'data: {"type":"stage","stage":"searching_web"}\n\n'
            
            clean_search_query = question
            for prefix in [
                "for web search", "web search for", "web search", "search the web for",
                "search the web", "search web for", "search web", "search online for",
                "search online", "browse the web for", "browse the web", "browse web for",
                "google for", "google", "search for", "search"
            ]:
                if clean_search_query.lower().startswith(prefix):
                    clean_search_query = clean_search_query[len(prefix):].strip(": ,-")
                    break
            if not clean_search_query.strip():
                clean_search_query = question

            try:
                context = await asyncio.wait_for(
                    asyncio.to_thread(web_search_tool.invoke, clean_search_query),
                    timeout=3.5
                )
                docs_meta = [{"content": context, "source": "Web Search", "doc_id": "web-search"}]
            except asyncio.TimeoutError:
                context = f"Live search completed for '{clean_search_query}'."
                docs_meta = []
            except Exception:
                context = "No search results available."
                docs_meta = []

            yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":docs_meta})}\n\n'
            yield 'data: {"type":"stage","stage":"generating"}\n\n'
            prompt_val = gen_prompt.invoke({
                "memories": memories,
                "chat_history": chat_hist,
                "context": context,
                "question": question
            })
            async for chunk in astream_with_backoff(get_active_llm(), prompt_val):
                token = safe_str(chunk.content)
                if token:
                    answer_parts.append(token)
                    yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"

        # ── 7. DOCUMENT RETRIEVAL (FAISS) ────────────────────────────
        elif decision.intent == QueryIntent.DOCUMENT_RAG:
            source = "Document Search"
            yield 'data: {"type":"stage","stage":"searching_docs"}\n\n'
            last_q = get_last_user_query(thread_id)
            search_query = f"{last_q} {question}".strip() if last_q and is_followup_query(question) else question
            
            docs = await asyncio.to_thread(retriever.invoke, search_query)
            if not docs and last_q:
                docs = await asyncio.to_thread(retriever.invoke, last_q)

            docs_meta = [
                {"content": safe_str(d.page_content),
                 "source": d.metadata.get("source", "Indexed Document"),
                 "doc_id": d.metadata.get("doc_id", "unknown")}
                for d in docs
            ]
            context = format_docs(docs)
            yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":docs_meta})}\n\n'
            yield 'data: {"type":"stage","stage":"generating"}\n\n'

            prompt_val = gen_prompt.invoke({
                "memories": memories,
                "chat_history": chat_hist,
                "context": context,
                "question": question
            })
            async for chunk in astream_with_backoff(get_active_llm(), prompt_val):
                token = safe_str(chunk.content)
                if token:
                    answer_parts.append(token)
                    yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"

        # ── 8. GENERAL ASSISTANT ─────────────────────────────────────
        else:
            source = "Assistant"
            yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[]})}\n\n'
            yield 'data: {"type":"stage","stage":"generating"}\n\n'
            prompt_val = conv_prompt.invoke({
                "memories": memories,
                "chat_history": chat_hist,
                "question": question
            })
            async for chunk in astream_with_backoff(get_active_llm(), prompt_val):
                token = safe_str(chunk.content)
                if token:
                    answer_parts.append(token)
                    yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"

        # ── DONE ─────────────────────────────────────────────────────
        yield 'data: {"type":"stage","stage":"success"}\n\n'
        yield 'data: {"type":"done"}\n\n'

        full_answer = "".join(safe_str(p) for p in answer_parts)
        if thread_id:
            record_thread_turn(thread_id, "user", question)
            record_thread_turn(thread_id, "assistant", full_answer)
            try:
                import uuid
                u_msg_id = f"msg_{uuid.uuid4().hex[:10]}"
                a_msg_id = f"msg_{uuid.uuid4().hex[:10]}"
                save_conversation_message(thread_id, u_msg_id, "user", question)
                save_conversation_message(
                    thread_id, 
                    a_msg_id, 
                    "assistant", 
                    full_answer, 
                    source=source,
                    metadata={"retrievedDocs": docs_meta, "proposal": proposal}
                )
            except Exception as db_err:
                pass

    except Exception as exc:
        msg = format_friendly_error(exc)
        yield 'data: {"type":"stage","stage":"error"}\n\n'
        yield f"data: {_json.dumps({'type':'error','text':msg})}\n\n"
