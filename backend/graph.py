from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from langchain_core.output_parsers import StrOutputParser

from backend.config import get_llm
from backend.embeddings import safe_str
from backend.vector_store import vector_store, retriever, format_docs
from backend.tools import (
    web_search_tool,
    is_conversational_query,
    is_explicit_web_search,
    detect_gmail_intent,
    detect_calendar_intent,
    detect_task_intent,
    detect_memory_intent
)
from backend.prompts import gen_prompt, conv_prompt
from backend.services.database import (
    list_tasks,
    create_task,
    complete_task,
    get_overdue_tasks,
    list_memories,
    add_memory,
    get_relevant_memories_text
)
from backend.services.google_service import (
    search_emails,
    read_email,
    summarize_email_thread,
    create_email_draft,
    list_calendar_events,
    check_calendar_availability,
    find_free_meeting_slots
)

class AgentState(TypedDict):
    question: str
    context: str
    answer: str
    source: str
    docs_metadata: list
    proposal: Optional[dict]
    model_name: Optional[str]
    thread_id: Optional[str]
    chat_history: Optional[str]

def conversation_node(state: AgentState) -> dict:
    model_name = state.get("model_name") or "gemini-3.5-flash-lite"
    chat_hist = state.get("chat_history") or "No prior conversational context."
    memories = get_relevant_memories_text()
    try:
        llm_inst = get_llm(model_name)
        reply = (conv_prompt | llm_inst | StrOutputParser()).invoke({
            "memories": memories,
            "chat_history": chat_hist,
            "question": state["question"]
        })
    except Exception as e:
        fallback_llm = get_llm("gemini-3.5-flash-lite")
        reply = (conv_prompt | fallback_llm | StrOutputParser()).invoke({
            "memories": memories,
            "chat_history": chat_hist,
            "question": state["question"]
        })
    return {
        "answer": reply.strip(),
        "source": "Assistant",
        "context": "",
        "docs_metadata": []
    }

def retrieve_node(state: AgentState) -> dict:
    docs = retriever.invoke(state["question"])
    doc_items = [
        {
            "content": safe_str(d.page_content),
            "source": d.metadata.get("source", "Indexed Document"),
            "doc_id": d.metadata.get("doc_id", "unknown")
        }
        for d in docs
    ]
    return {
        "context": format_docs(docs),
        "source": "Document Search",
        "docs_metadata": doc_items
    }

def web_search_node(state: AgentState) -> dict:
    question = state["question"]
    try:
        search_results = web_search_tool.invoke(question)
    except Exception:
        search_results = "No web search results available."
    return {
        "context": search_results,
        "source": "Web Search",
        "docs_metadata": [{"content": search_results, "source": "Web Search", "doc_id": "web-search"}]
    }

def gmail_node(state: AgentState) -> dict:
    intent_data = detect_gmail_intent(state["question"])
    intent_type = intent_data[0] if intent_data else "search_emails"
    params = intent_data[1] if intent_data else {}
    
    if intent_type == "search_emails":
        results = search_emails(params.get("query", ""))
        lines = []
        for em in results:
            if "status" in em and em["status"] == "not_connected":
                lines.append("Google account not connected. Please connect your Google account in Settings to search your emails.")
                break
            lines.append(f"- From: {em.get('sender')} | Subject: {em.get('subject')} | Date: {em.get('date')}\n  Snippet: {em.get('snippet')}")
        context = "\n".join(lines) if lines else "No emails found matching your query."
    elif intent_type == "create_draft":
        to_email = params.get("to", "recipient@example.com")
        draft_res = create_email_draft(to=to_email, subject="Follow up", body="Hello,\n\nFollowing up on our conversation.")
        context = f"Draft creation result: {draft_res.get('message', 'Completed')}"
    else:
        context = "Gmail operation processed."
        
    return {
        "context": context,
        "source": "Gmail",
        "docs_metadata": [{"content": context, "source": "Gmail", "doc_id": "gmail"}]
    }

def calendar_node(state: AgentState) -> dict:
    intent_data = detect_calendar_intent(state["question"])
    intent_type = intent_data[0] if intent_data else "list_events"
    
    if intent_type == "check_availability":
        slots = find_free_meeting_slots(duration_minutes=30)
        lines = ["Available meeting slots in your calendar:"]
        for s in slots:
            lines.append(f"- {s.get('start')} to {s.get('end')}")
        context = "\n".join(lines)
    else:
        events = list_calendar_events(max_results=5)
        lines = []
        for ev in events:
            if "status" in ev and ev["status"] == "not_connected":
                lines.append("Google account not connected. Please connect your Google account in Settings to view your calendar.")
                break
            lines.append(f"- Event: {ev.get('summary')} | Start: {ev.get('start')} | End: {ev.get('end')}")
        context = "\n".join(lines) if lines else "No upcoming events found on your primary calendar."
        
    return {
        "context": context,
        "source": "Google Calendar",
        "docs_metadata": [{"content": context, "source": "Google Calendar", "doc_id": "calendar"}]
    }

def task_node(state: AgentState) -> dict:
    intent_data = detect_task_intent(state["question"])
    intent_type = intent_data[0] if intent_data else "list_tasks"
    params = intent_data[1] if intent_data else {}
    
    if intent_type == "create_task":
        title = params.get("title", state["question"])
        task = create_task(title=title)
        context = f"Successfully created task: '{task['title']}' (ID: {task['id']}, Priority: {task['priority']})."
    elif intent_type == "list_overdue":
        overdue = get_overdue_tasks()
        if not overdue:
            context = "You have no overdue tasks! All deadlines are on track."
        else:
            lines = ["Overdue tasks:"]
            for t in overdue:
                lines.append(f"- [OVERDUE] {t['title']} (Due: {t['due_date']}, Priority: {t['priority']})")
            context = "\n".join(lines)
    else:
        tasks = list_tasks()
        if not tasks:
            context = "You currently have no tasks in your task manager. You can create one anytime (e.g. 'Create task to finish report by Friday')."
        else:
            lines = ["Your current tasks:"]
            for t in tasks:
                status_icon = "✓" if t["status"] == "completed" else "○"
                due_info = f" | Due: {t['due_date']}" if t['due_date'] else ""
                lines.append(f"- {status_icon} [{t['priority'].upper()}] {t['title']}{due_info} (Status: {t['status']})")
            context = "\n".join(lines)
            
    return {
        "context": context,
        "source": "Tasks & Reminders",
        "docs_metadata": [{"content": context, "source": "Tasks & Reminders", "doc_id": "tasks"}]
    }

def memory_node(state: AgentState) -> dict:
    intent_data = detect_memory_intent(state["question"])
    intent_type = intent_data[0] if intent_data else "list_memories"
    params = intent_data[1] if intent_data else {}
    
    if intent_type == "add_memory":
        content = params.get("content", state["question"])
        add_memory(content=content)
        context = f"Saved to persistent long-term memory: '{content}'."
    else:
        mems = list_memories()
        if not mems:
            context = "No persistent memories saved yet."
        else:
            lines = ["Saved long-term preferences & memories:"]
            for m in mems:
                lines.append(f"- [{m['category'].upper()}] {m['content']}")
            context = "\n".join(lines)
            
    return {
        "context": context,
        "source": "Long-Term Memory",
        "docs_metadata": [{"content": context, "source": "Long-Term Memory", "doc_id": "memory"}]
    }

def generate_node(state: AgentState) -> dict:
    model_name = state.get("model_name") or "gemini-3.5-flash-lite"
    chat_hist = state.get("chat_history") or "No prior conversational context."
    memories = get_relevant_memories_text()
    try:
        llm_inst = get_llm(model_name)
        answer = (gen_prompt | llm_inst | StrOutputParser()).invoke({
            "memories": memories,
            "chat_history": chat_hist,
            "context": state["context"],
            "question": state["question"]
        })
    except Exception:
        fallback_llm = get_llm("gemini-3.5-flash-lite")
        answer = (gen_prompt | fallback_llm | StrOutputParser()).invoke({
            "memories": memories,
            "chat_history": chat_hist,
            "context": state["context"],
            "question": state["question"]
        })
    return {"answer": answer}

# Router from START
def route_start(state: AgentState) -> str:
    question = state["question"].strip()
    
    # 1. Greetings & Small talk
    if is_conversational_query(question):
        return "conversation"
        
    # 2. Gmail intent
    if detect_gmail_intent(question):
        return "gmail"
        
    # 3. Calendar intent
    if detect_calendar_intent(question):
        return "calendar"
        
    # 4. Task intent
    if detect_task_intent(question):
        return "tasks"
        
    # 5. Memory intent
    if detect_memory_intent(question):
        return "memory"
        
    # 6. Explicit web search
    if is_explicit_web_search(question):
        return "web_search"
        
    # 7. Document search if documents indexed
    if len(vector_store.index_to_docstore_id) > 0:
        return "retrieve"
        
    return "conversation"

# Build StateGraph
workflow = StateGraph(AgentState)
workflow.add_node("conversation", conversation_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("web_search", web_search_node)
workflow.add_node("gmail", gmail_node)
workflow.add_node("calendar", calendar_node)
workflow.add_node("tasks", task_node)
workflow.add_node("memory", memory_node)
workflow.add_node("generate", generate_node)

workflow.add_conditional_edges(
    START,
    route_start,
    {
        "conversation": "conversation",
        "retrieve": "retrieve",
        "web_search": "web_search",
        "gmail": "gmail",
        "calendar": "calendar",
        "tasks": "tasks",
        "memory": "memory"
    }
)

workflow.add_edge("conversation", END)
workflow.add_edge("retrieve", "generate")
workflow.add_edge("web_search", "generate")
workflow.add_edge("gmail", "generate")
workflow.add_edge("calendar", "generate")
workflow.add_edge("tasks", "generate")
workflow.add_edge("memory", "generate")
workflow.add_edge("generate", END)

rag_app = workflow.compile()
