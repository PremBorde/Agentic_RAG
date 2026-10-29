from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

from backend.vector_store import indexed_documents, clear_vector_store
from backend.services.document_service import (
    process_uploaded_file, 
    process_custom_text, 
    process_youtube_url
)

router = APIRouter(prefix="/api/documents", tags=["documents"])

class AddDocRequest(BaseModel):
    title: str
    content: str

class YouTubeDocRequest(BaseModel):
    url: str
    title: str = ""

@router.get("")
def list_documents():
    """Returns all currently indexed documents in the vector store."""
    return {
        "documents": indexed_documents,
        "total_chunks": sum(d.get("chunk_count", 0) for d in indexed_documents)
    }

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Uploads a PDF, TXT, or MD file and indexes directly into FAISS."""
    return await process_uploaded_file(file)

@router.post("/add")
def add_custom_document(req: AddDocRequest):
    """Manually adds raw text / notes into the vector store."""
    return process_custom_text(req.title, req.content)

@router.post("/youtube")
def add_youtube_transcript(req: YouTubeDocRequest):
    """Fetches video transcript from YouTube and indexes it into the vector store."""
    return process_youtube_url(req.url, req.title)

@router.delete("/clear")
def clear_documents():
    """Clears all indexed documents from the vector store."""
    clear_vector_store()
    return {"message": "All documents successfully removed."}

