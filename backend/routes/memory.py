from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from backend.utils.auth import get_current_user_id
from backend.services.database import add_memory, list_memories, delete_memory

router = APIRouter(prefix="/api/memories", tags=["Long-Term Memory"])

class MemoryCreateRequest(BaseModel):
    content: str
    category: Optional[str] = "preference"

@router.get("")
def get_memories(request: Request, category: Optional[str] = None):
    """Retrieves saved long-term user preferences and context."""
    user_id = get_current_user_id(request)
    return list_memories(category, user_id=user_id)

@router.post("")
def create_memory(req: MemoryCreateRequest, request: Request):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    user_id = get_current_user_id(request)
    return add_memory(req.content, req.category or "preference", user_id=user_id)

@router.delete("/{memory_id}")
def remove_memory(memory_id: str, request: Request):
    user_id = get_current_user_id(request)
    success = delete_memory(memory_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found or access denied")
    return {"success": True, "message": "Memory deleted"}

