from fastapi import APIRouter, UploadFile, File, Request
from pydantic import BaseModel
from typing import Optional

from backend.vector_store import indexed_documents, clear_vector_store, delete_document
from backend.services.document_service import (
    process_uploaded_file, 
    process_custom_text, 
    process_youtube_url,
    remove_document
)
from backend.utils.auth import get_current_user_id

router = APIRouter(prefix="/api/documents", tags=["documents"])

class AddDocRequest(BaseModel):
    title: str
    content: str

class YouTubeDocRequest(BaseModel):
    url: str
    title: str = ""

@router.get("")
def list_documents(request: Request):
    """Returns all currently indexed documents in the vector store scoped to user if authenticated."""
    user_id = get_current_user_id(request)
    if user_id:
        docs = [d for d in indexed_documents if not d.get("user_id") or d.get("user_id") == user_id]
    else:
        docs = indexed_documents
    return {
        "documents": docs,
        "total_chunks": sum(d.get("chunk_count", 0) for d in docs)
    }

@router.post("/upload")
async def upload_document(request: Request, file: UploadFile = File(...)):
    """Uploads a PDF, TXT, or MD file and indexes directly into FAISS."""
    user_id = get_current_user_id(request)
    return await process_uploaded_file(file, user_id=user_id)

@router.post("/add")
def add_custom_document(req: AddDocRequest, request: Request):
    """Manually adds raw text / notes into the vector store."""
    user_id = get_current_user_id(request)
    return process_custom_text(req.title, req.content, user_id=user_id)

@router.post("/youtube")
def add_youtube_transcript(req: YouTubeDocRequest, request: Request):
    """Fetches video transcript from YouTube and indexes it into the vector store."""
    user_id = get_current_user_id(request)
    return process_youtube_url(req.url, req.title, user_id=user_id)

@router.delete("/clear")
@router.post("/clear")
def clear_documents(request: Request):
    """Clears indexed documents from the vector store."""
    user_id = get_current_user_id(request)
    if user_id:
        user_targets = [d.get("id") for d in indexed_documents if d.get("user_id") == user_id]
        for target_id in user_targets:
            delete_document(target_id)
    else:
        clear_vector_store()
    return {"message": "All documents successfully removed."}

@router.delete("/{doc_id:path}")
def delete_document_by_id(doc_id: str, request: Request):
    """Deletes a specific document from the vector store by ID or title with ownership verification."""
    user_id = get_current_user_id(request)
    return remove_document(doc_id, user_id=user_id)
