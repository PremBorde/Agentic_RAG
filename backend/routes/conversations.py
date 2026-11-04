import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from backend.services.database import (
    list_conversations,
    get_conversation_with_messages,
    create_or_update_conversation,
    save_conversation_thread_batch,
    save_conversation_message,
    delete_conversation_thread,
    get_conversation_owner,
    get_db_connection
)
from backend.utils.auth import get_current_user_id

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

def _resolve_user_id(request: Request) -> str:
    """Resolves authenticated user_id or assigns a deterministic session guest ID."""
    uid = get_current_user_id(request)
    if uid:
        return uid
    if hasattr(request, "session"):
        if "guest_id" not in request.session:
            request.session["guest_id"] = f"guest_{uuid.uuid4().hex[:12]}"
        return request.session["guest_id"]
    return "guest_default"

def _assert_ownership(thread_id: str, active_user_id: str):
    """Enforces strict multi-user ownership check."""
    owner = get_conversation_owner(thread_id)
    if owner is not None and owner != active_user_id:
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: You do not have permission to view or modify this conversation."
        )

class SyncConversationRequest(BaseModel):
    thread_id: str
    title: str
    model: str = "gemini-3.5-flash-lite"
    messages: List[Dict[str, Any]] = []
    user_id: Optional[str] = None

class RenameConversationRequest(BaseModel):
    title: str

class UpdateConversationRequest(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None
    archived: Optional[bool] = None

class CreateMessageRequest(BaseModel):
    text: str
    sender: str = "user"
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@router.get("")
def get_all_conversations(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Retrieves all conversation threads owned by the authenticated user / active session."""
    active_user = _resolve_user_id(request)
    threads = list_conversations(user_id=active_user, limit=limit, offset=offset)
    return {"conversations": threads}

@router.get("/{thread_id}")
def get_single_conversation(
    thread_id: str,
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Retrieves a single conversation thread along with its persisted messages after ownership check."""
    active_user = _resolve_user_id(request)
    _assert_ownership(thread_id, active_user)

    conv = get_conversation_with_messages(thread_id, message_limit=limit, message_offset=offset)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation thread not found.")
    return conv

@router.post("")
def sync_conversation(req: SyncConversationRequest, request: Request):
    """Saves or updates a conversation thread bound strictly to the active user."""
    active_user = _resolve_user_id(request)
    _assert_ownership(req.thread_id, active_user)

    save_conversation_thread_batch(
        thread_id=req.thread_id,
        title=req.title,
        model=req.model,
        messages=req.messages,
        user_id=active_user
    )
    return {"status": "success", "thread_id": req.thread_id}

@router.patch("/{thread_id}/title")
def rename_conversation(thread_id: str, req: RenameConversationRequest, request: Request):
    """Renames an existing conversation title with ownership enforcement."""
    active_user = _resolve_user_id(request)
    _assert_ownership(thread_id, active_user)

    create_or_update_conversation(thread_id=thread_id, title=req.title)
    return {"status": "success", "thread_id": thread_id, "title": req.title}

@router.patch("/{thread_id}")
def update_conversation(thread_id: str, req: UpdateConversationRequest, request: Request):
    """Updates conversation attributes (title, model, archive status) with ownership check."""
    active_user = _resolve_user_id(request)
    _assert_ownership(thread_id, active_user)

    conn = get_db_connection()
    updates = []
    params = []
    if req.title is not None:
        updates.append("title = ?")
        params.append(req.title)
    if req.model is not None:
        updates.append("model = ?")
        params.append(req.model)
    if req.archived is not None:
        updates.append("archived_at = ?")
        params.append(datetime.utcnow().isoformat() if req.archived else None)

    if updates:
        params.append(thread_id)
        conn.execute(f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()
    return {"status": "success", "thread_id": thread_id}

@router.delete("/{thread_id}")
def delete_conversation(thread_id: str, request: Request):
    """Permanently deletes a conversation thread and all its messages after ownership verification."""
    active_user = _resolve_user_id(request)
    _assert_ownership(thread_id, active_user)

    deleted = delete_conversation_thread(thread_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found or already deleted.")
    return {"status": "success", "message": f"Conversation '{thread_id}' deleted."}

@router.get("/{thread_id}/messages")
def get_thread_messages(
    thread_id: str,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Retrieves paginated messages for a conversation thread with ownership check."""
    active_user = _resolve_user_id(request)
    _assert_ownership(thread_id, active_user)

    conv = get_conversation_with_messages(thread_id, message_limit=limit, message_offset=offset)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation thread not found.")
    return {"messages": conv.get("messages", []), "thread_id": thread_id}

@router.post("/{thread_id}/messages")
def post_thread_message(thread_id: str, req: CreateMessageRequest, request: Request):
    """Appends an individual message to the thread with immediate persistence and ownership validation."""
    active_user = _resolve_user_id(request)
    _assert_ownership(thread_id, active_user)

    msg_id = f"msg_{uuid.uuid4().hex[:10]}"
    saved = save_conversation_message(
        thread_id=thread_id,
        msg_id=msg_id,
        sender=req.sender,
        text=req.text,
        source=req.source,
        metadata=req.metadata,
        user_id=active_user
    )
    return {"status": "success", "message": saved}

threads_router = APIRouter(prefix="/api/threads", tags=["threads"])

@threads_router.delete("/{thread_id}")
def delete_thread_legacy(thread_id: str, request: Request):
    active_user = _resolve_user_id(request)
    _assert_ownership(thread_id, active_user)
    delete_conversation_thread(thread_id)
    return {"status": "success", "message": f"Thread '{thread_id}' deleted."}
