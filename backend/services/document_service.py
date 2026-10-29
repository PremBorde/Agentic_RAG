import io
import re
from datetime import datetime
from fastapi import UploadFile, HTTPException
import pypdf
from youtube_transcript_api import YouTubeTranscriptApi

from backend.embeddings import splitter
from backend.vector_store import vector_store, indexed_documents

def extract_youtube_video_id(url_or_id: str) -> str:
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"^([0-9A-Za-z_-]{11})$"
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return url_or_id.strip()

async def process_uploaded_file(file: UploadFile) -> dict:
    filename = file.filename or "uploaded_document"
    content = ""
    
    try:
        if filename.lower().endswith(".pdf"):
            pdf_bytes = await file.read()
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            extracted_pages = [page.extract_text() or "" for page in reader.pages]
            content = "\n\n".join(extracted_pages).strip()
        else:
            bytes_data = await file.read()
            content = bytes_data.decode("utf-8", errors="ignore").strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
        
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty or contains no readable text.")
        
    new_chunks = splitter.split_text(content)
    if not new_chunks:
        raise HTTPException(status_code=400, detail="File content was too short to generate chunks.")
        
    doc_id = f"file-{len(indexed_documents) + 1}-{int(datetime.now().timestamp())}"
    try:
        vector_store.add_texts(
            new_chunks,
            metadatas=[{"source": filename, "doc_id": doc_id}] * len(new_chunks)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index file into vector store: {str(e)}")
        
    doc_entry = {
        "id": doc_id,
        "title": filename,
        "source_type": "file",
        "chunk_count": len(new_chunks),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "preview": content[:240] + ("..." if len(content) > 240 else ""),
        "full_content": content
    }
    indexed_documents.append(doc_entry)
    
    return {
        "message": f"Successfully indexed '{filename}' into {len(new_chunks)} chunks.",
        "document": doc_entry
    }

def process_custom_text(title: str, content: str) -> dict:
    clean_title = title.strip() or "Untitled Note"
    clean_content = content.strip()
    
    new_chunks = splitter.split_text(clean_content)
    if not new_chunks:
        raise HTTPException(status_code=400, detail="Content was too short to generate chunks.")
        
    doc_id = f"note-{len(indexed_documents) + 1}-{int(datetime.now().timestamp())}"
    try:
        vector_store.add_texts(
            new_chunks,
            metadatas=[{"source": clean_title, "doc_id": doc_id}] * len(new_chunks)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index text into vector store: {str(e)}")
        
    doc_entry = {
        "id": doc_id,
        "title": clean_title,
        "source_type": "custom_text",
        "chunk_count": len(new_chunks),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "preview": clean_content[:240] + ("..." if len(clean_content) > 240 else ""),
        "full_content": clean_content
    }
    indexed_documents.append(doc_entry)
    
    return {
        "message": f"Successfully indexed '{clean_title}' into {len(new_chunks)} chunks.",
        "document": doc_entry
    }

def process_youtube_url(url: str, custom_title: str = "") -> dict:
    video_id = extract_youtube_video_id(url)
    try:
        data = YouTubeTranscriptApi().get_transcript(video_id)
        transcript = " ".join(c.text if hasattr(c, "text") else c["text"] for c in data)
    except Exception:
        try:
            data = YouTubeTranscriptApi.get_transcript(video_id)
            transcript = " ".join(c["text"] for c in data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not retrieve YouTube transcript: {str(e)}")

    if not transcript:
        raise HTTPException(status_code=400, detail="YouTube video had no transcript available.")

    title = custom_title.strip() if custom_title else f"YouTube Video ({video_id})"
    new_chunks = splitter.split_text(transcript)
    if not new_chunks:
        raise HTTPException(status_code=400, detail="Video transcript was too short to generate chunks.")
        
    doc_id = f"yt-{len(indexed_documents) + 1}-{int(datetime.now().timestamp())}"
    try:
        vector_store.add_texts(
            new_chunks,
            metadatas=[{"source": title, "doc_id": doc_id}] * len(new_chunks)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index YouTube transcript: {str(e)}")
        
    doc_entry = {
        "id": doc_id,
        "title": title,
        "source_type": "youtube",
        "chunk_count": len(new_chunks),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "preview": transcript[:240] + ("..." if len(transcript) > 240 else ""),
        "full_content": transcript
    }
    indexed_documents.append(doc_entry)
    
    return {
        "message": f"Successfully indexed YouTube video into {len(new_chunks)} chunks.",
        "document": doc_entry
    }

