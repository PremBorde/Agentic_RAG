import json as _json
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

from backend.config import get_llm
from backend.utils.retry import astream_with_backoff, format_friendly_error
from backend.embeddings import safe_str
from backend.vector_store import vector_store, retriever, format_docs
from backend.tools import (
    is_conversational_query,
    is_explicit_web_search,
    is_followup_query,
    web_search_tool,
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
    get_relevant_memories_text
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
    doc_count = len(vector_store.index_to_docstore_id)
    source = "Assistant"
    docs_meta = []
    context = ""
    answer_parts: list[str] = []
    proposal = None

    try:
        yield 'data: {"type":"stage","stage":"thinking"}\n\n'
        llm = get_llm(model_name)

        # ── 1. GMAIL ROUTING ─────────────────────────────────────────
        gmail_intent = detect_gmail_intent(question)
        if gmail_intent:
            action_name, params = gmail_intent
            source = "Gmail"
            is_google_connected = get_connection_status(user_id).get("connected", False)
            
            if not is_google_connected:
                yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[],"requires_google_auth":True})}\n\n'
                yield 'data: {"type":"stage","stage":"generating"}\n\n'
                friendly_msg = (
                    "### 🔒 Google Workspace is Not Connected\n\n"
                    "I noticed you requested a Gmail operation, but your Google account is currently not connected (or your authentication token has expired).\n\n"
                    "To search emails, read conversation threads, draft messages, or send updates, please connect your Google account below:"
                )
                yield f"data: {_json.dumps({'type':'token','text':friendly_msg})}\n\n"
                answer_parts.append(friendly_msg)

            # Sensitive: Sending an Email -> Propose Action
            elif action_name == "send_email":
                to_addr = params.get("to", "recipient@example.com")
                subj = params.get("subject", "Project Update")
                body = (
                    f"Hi,\n\nI am writing to share our project updates as requested.\n\n"
                    f"Best regards,\nPersonal AI Agent"
                )
                proposal = propose_action(
                    action_type="send_email",
                    summary=f"Send email to {to_addr} with subject '{subj}'",
                    payload={"to": to_addr, "subject": subj, "body": body}
                )
                
                yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[],"proposal":proposal})}\n\n'
                yield 'data: {"type":"stage","stage":"generating"}\n\n'
                
                preview_msg = (
                    f"I have prepared the email for **{to_addr}** with subject **\"{subj}\"**.\n\n"
                    f"Please review the proposed action card below and click **Approve** to send, or **Cancel** if you'd like to make changes."
                )
                yield f"data: {_json.dumps({'type':'token','text':preview_msg})}\n\n"
                answer_parts.append(preview_msg)

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
                emails = search_emails(query=query_str, max_results=5, user_id=user_id)
                
                lines = []
                for em in emails:
                    if em.get("status") == "not_connected":
                        lines.append("Google account not connected. Please connect your Google account in Settings to access Gmail.")
                        break
                    lines.append(f"- **From:** {em.get('sender')} | **Subject:** {em.get('subject')} | **Date:** {em.get('date')}\n  {em.get('snippet')}")
                context = "\n\n".join(lines) if lines else "No matching emails found in your Gmail inbox."
                
                docs_meta = [{"content": context, "source": "Gmail", "doc_id": "gmail"}]
                yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":docs_meta})}\n\n'
                yield 'data: {"type":"stage","stage":"generating"}\n\n'
                
                prompt_val = gen_prompt.invoke({
                    "memories": memories,
                    "chat_history": chat_hist,
                    "context": context,
                    "question": question
                })
                async for chunk in astream_with_backoff(llm, prompt_val):
                    token = safe_str(chunk.content)
                    if token:
                        answer_parts.append(token)
                        yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"

        # ── 2. CALENDAR ROUTING ──────────────────────────────────────
        elif detect_calendar_intent(question):
            cal_intent = detect_calendar_intent(question)
            action_name, params = cal_intent
            source = "Google Calendar"
            is_google_connected = get_connection_status(user_id).get("connected", False)
            
            if not is_google_connected:
                yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[],"requires_google_auth":True})}\n\n'
                yield 'data: {"type":"stage","stage":"generating"}\n\n'
                friendly_msg = (
                    "### 🔒 Google Workspace is Not Connected\n\n"
                    "I noticed you requested a Calendar operation, but your Google account is currently not connected (or your authentication token has expired).\n\n"
                    "To check upcoming meetings, verify free slots, or schedule calendar events, please connect your Google account below:"
                )
                yield f"data: {_json.dumps({'type':'token','text':friendly_msg})}\n\n"
                answer_parts.append(friendly_msg)

            # Sensitive: Creating a Calendar Event -> Propose Action
            elif action_name == "create_event":
                source = "Google Calendar"
                start_dt = (datetime.now() + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
                end_dt = start_dt + timedelta(minutes=45)
                
                proposal = propose_action(
                    action_type="create_calendar_event",
                    summary="Schedule Project Planning Meeting",
                    payload={
                        "summary": "Project Planning Meeting",
                        "start_time": start_dt.isoformat() + "Z",
                        "end_time": end_dt.isoformat() + "Z",
                        "description": "Agenda: Discuss timeline, milestones, and deliverable status.",
                        "attendees": []
                    }
                )
                yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[],"proposal":proposal})}\n\n'
                yield 'data: {"type":"stage","stage":"generating"}\n\n'
                
                preview_msg = (
                    f"I have checked your schedule and formulated an event proposal:\n\n"
                    f"- **Event:** Project Planning Meeting\n"
                    f"- **Proposed Time:** {start_dt.strftime('%A, %b %d, %Y at %I:%M %p')}\n"
                    f"- **Duration:** 45 minutes\n\n"
                    f"Please review the proposed action card below and click **Approve** to confirm and add it to your calendar."
                )
                yield f"data: {_json.dumps({'type':'token','text':preview_msg})}\n\n"
                answer_parts.append(preview_msg)

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
                async for chunk in astream_with_backoff(llm, prompt_val):
                    token = safe_str(chunk.content)
                    if token:
                        answer_parts.append(token)
                        yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"

            # Listing Calendar Events
            else:
                source = "Google Calendar"
                yield 'data: {"type":"stage","stage":"checking_calendar"}\n\n'
                events = list_calendar_events(max_results=5, user_id=user_id)
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
                async for chunk in astream_with_backoff(llm, prompt_val):
                    token = safe_str(chunk.content)
                    if token:
                        answer_parts.append(token)
                        yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"

        # ── 3. TASK & REMINDER ROUTING ───────────────────────────────
        elif detect_task_intent(question):
            task_intent = detect_task_intent(question)
            action_name, params = task_intent
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

        # ── 4. LONG-TERM MEMORY ROUTING ──────────────────────────────
        elif detect_memory_intent(question):
            mem_intent = detect_memory_intent(question)
            action_name, params = mem_intent
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

        # ── 5. CONVERSATIONAL GREETINGS & INTRO ───────────────────────
        elif is_conversational_query(question):
            source = "Assistant"
            yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[]})}\n\n'
            yield 'data: {"type":"stage","stage":"generating"}\n\n'
            prompt_val = conv_prompt.invoke({
                "memories": memories,
                "chat_history": chat_hist,
                "question": question
            })
            async for chunk in astream_with_backoff(llm, prompt_val):
                token = safe_str(chunk.content)
                if token:
                    answer_parts.append(token)
                    yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"

        # ── 6. EXPLICIT WEB SEARCH ───────────────────────────────────
        elif is_explicit_web_search(question):
            source = "Web Search"
            yield 'data: {"type":"stage","stage":"searching_web"}\n\n'
            try:
                context = web_search_tool.invoke(question)
                docs_meta = [{"content": context, "source": "Web Search", "doc_id": "web-search"}]
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
            async for chunk in astream_with_backoff(llm, prompt_val):
                token = safe_str(chunk.content)
                if token:
                    answer_parts.append(token)
                    yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"

        # ── 7. DOCUMENT RETRIEVAL (FAISS) ────────────────────────────
        elif doc_count > 0:
            source = "Document Search"
            yield 'data: {"type":"stage","stage":"searching_docs"}\n\n'
            last_q = get_last_user_query(thread_id)
            search_query = f"{last_q} {question}".strip() if last_q and is_followup_query(question) else question
            
            docs = retriever.invoke(search_query)
            if not docs and last_q:
                docs = retriever.invoke(last_q)

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
            async for chunk in astream_with_backoff(llm, prompt_val):
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
            async for chunk in astream_with_backoff(llm, prompt_val):
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

    except Exception as exc:
        msg = format_friendly_error(exc)
        yield 'data: {"type":"stage","stage":"error"}\n\n'
        yield f"data: {_json.dumps({'type':'error','text':msg})}\n\n"
