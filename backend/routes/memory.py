from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.services.database import add_memory, list_memories, delete_memory

router = APIRouter(prefix="/api/memories", tags=["Long-Term Memory"])

class MemoryCreateRequest(BaseModel):
    content: str
    category: Optional[str] = "preference"

@router.get("")
def get_memories(category: Optional[str] = None):
    """Retrieves saved long-term user preferences and context."""
    return list_memories(category)

@router.post("")
def create_memory(req: MemoryCreateRequest):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    return add_memory(req.content, req.category or "preference")

@router.delete("/{memory_id}")
def remove_memory(memory_id: str):
    success = delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True, "message": "Memory deleted"}
