from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from backend.services.database import (
    list_conversations,
    get_conversation_with_messages,
    create_or_update_conversation,
    save_conversation_thread_batch,
    delete_conversation_thread
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

class SyncConversationRequest(BaseModel):
    thread_id: str
    title: str
    model: str = "gemini-3.5-flash-lite"
    messages: List[Dict[str, Any]] = []
    user_id: Optional[str] = None

class RenameConversationRequest(BaseModel):
    title: str

@router.get("")
def get_all_conversations(
    user_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Retrieves all conversation threads sorted by most recent activity."""
    threads = list_conversations(user_id=user_id, limit=limit, offset=offset)
    return {"conversations": threads}

@router.get("/{thread_id}")
def get_single_conversation(
    thread_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Retrieves a single conversation thread along with its persisted messages."""
    conv = get_conversation_with_messages(thread_id, message_limit=limit, message_offset=offset)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation thread not found.")
    return conv

@router.post("")
def sync_conversation(req: SyncConversationRequest):
    """Saves or updates a conversation thread and its messages in SQLite."""
    save_conversation_thread_batch(
        thread_id=req.thread_id,
        title=req.title,
        model=req.model,
        messages=req.messages,
        user_id=req.user_id
    )
    return {"status": "success", "thread_id": req.thread_id}

@router.patch("/{thread_id}/title")
def rename_conversation(thread_id: str, req: RenameConversationRequest):
    """Renames an existing conversation title."""
    create_or_update_conversation(thread_id=thread_id, title=req.title)
    return {"status": "success", "thread_id": thread_id, "title": req.title}

@router.delete("/{thread_id}")
def delete_conversation(thread_id: str):
    """Permanently deletes a conversation thread and all its messages."""
    deleted = delete_conversation_thread(thread_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found or already deleted.")
    return {"status": "success", "message": f"Conversation '{thread_id}' deleted."}

