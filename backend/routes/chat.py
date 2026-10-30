from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.config import AVAILABLE_MODELS
from backend.utils.retry import format_friendly_error
from backend.utils.auth import get_current_user_id
from backend.graph import rag_app
from backend.memory import get_thread_context_str, record_thread_turn
from backend.services.chat_service import stream_chat_events

router = APIRouter(prefix="/api", tags=["chat"])

class QueryRequest(BaseModel):
    message: str
    model: Optional[str] = "gemini-3.5-flash-lite"
    thread_id: Optional[str] = None

@router.get("/models")
def get_available_models():
    """Returns available Google Gemini models."""
    return {"models": AVAILABLE_MODELS}

@router.post("/chat")
def chat_sync(req: QueryRequest):
    """Synchronous LangGraph RAG execution."""
    question = req.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    chat_hist = get_thread_context_str(req.thread_id)
    initial_state = {
        "question": question,
        "context": "",
        "answer": "",
        "source": "",
        "docs_metadata": [],
        "model_name": req.model,
        "thread_id": req.thread_id,
        "chat_history": chat_hist
    }

    try:
        final_state = rag_app.invoke(initial_state)
        answer = final_state.get("answer", "")
        source = final_state.get("source", "Unknown")
        docs_meta = final_state.get("docs_metadata", [])

        if req.thread_id:
            record_thread_turn(req.thread_id, "user", question)
            record_thread_turn(req.thread_id, "assistant", answer)

        return {
            "answer": answer,
            "source": source,
            "retrieved_docs": docs_meta,
            "model_used": req.model
        }
    except Exception as e:
        msg = format_friendly_error(e)
        return {
            "answer": msg,
            "source": "System Notification",
            "retrieved_docs": []
        }

@router.post("/chat/stream")
async def chat_streaming(req: QueryRequest, request: Request):
    """Streaming LangGraph RAG execution with Server-Sent Events (SSE)."""
    question = req.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    model_name = req.model or "gemini-2.5-flash"
    user_id = get_current_user_id(request)

    return StreamingResponse(
        stream_chat_events(question, model_name, req.thread_id or "", user_id=user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

