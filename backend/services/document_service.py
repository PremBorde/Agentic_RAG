import os
import io
import re
import logging
from datetime import datetime
from fastapi import UploadFile, HTTPException
from youtube_transcript_api import YouTubeTranscriptApi

import backend.vector_store as vs_module
from backend.vector_store import (
    vector_store,
    indexed_documents,
    save_vector_store_to_disk,
    find_duplicate_document,
    compute_content_hash,
    delete_document
)
from backend.services.parsers import (
    parse_pdf,
    parse_docx,
    parse_csv,
    parse_json,
    parse_plain_or_markdown,
    clean_text_artifacts
)
from backend.services.chunking import chunk_document_sections
from backend.services.hybrid_retriever import hybrid_retriever

logger = logging.getLogger("document_service")

MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB limit
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".json"}

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
    raw_name = file.filename or "uploaded_document"
    clean_base = os.path.basename(raw_name).strip()
    filename = re.sub(r'[^a-zA-Z0-9_.\-\s]', '', clean_base) or "uploaded_document"
    ext = os.path.splitext(filename)[1].lower()
    title = filename

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    try:
        bytes_data = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read upload stream: {str(e)}")

    if len(bytes_data) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413, 
            detail=f"File exceeds maximum upload limit of 25MB (received {len(bytes_data) / (1024 * 1024):.1f}MB)."
        )

    # 1. Parse sections using format-specific parser
    sections = []
    try:
        if ext == ".pdf":
            sections = parse_pdf(bytes_data)
        elif ext == ".docx":
            sections = parse_docx(bytes_data)
        elif ext == ".csv":
            sections = parse_csv(bytes_data)
        elif ext == ".json":
            sections = parse_json(bytes_data)
        else:
            sections = parse_plain_or_markdown(bytes_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse document: {str(e)}")

    if not sections or not any(s.get("text") for s in sections):
        raise HTTPException(status_code=400, detail="Uploaded file is empty or contains no readable text.")

    full_content = "\n\n".join(s["text"] for s in sections).strip()
    content_hash = compute_content_hash(full_content)

    # 2. Deduplication check
    existing_doc = find_duplicate_document(full_content, filename)
    if existing_doc:
        return {
            "message": f"'{filename}' is already indexed in the Knowledge Base.",
            "document": existing_doc,
            "already_indexed": True
        }

    doc_id = f"file-{len(indexed_documents) + 1}-{int(datetime.now().timestamp())}"
    doc_type = ext.lstrip(".")

    # 3. Structure & sentence-boundary aware chunking
    chunks = chunk_document_sections(
        sections=sections,
        document_id=doc_id,
        document_name=filename,
        document_type=doc_type,
        content_hash=content_hash,
        chunk_size=500,
        chunk_overlap=75
    )

    if not chunks:
        raise HTTPException(status_code=400, detail="Document content was too short to generate indexable chunks.")

    # 4. Dual indexing: FAISS Vector Store + Lexical BM25 Index
    try:
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        vs_module.vector_store.add_texts(texts, metadatas=metadatas)
        hybrid_retriever.add_chunks(chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index document into vector store: {str(e)}")

    doc_entry = {
        "id": doc_id,
        "title": filename,
        "source_type": "file",
        "document_type": doc_type,
        "chunk_count": len(chunks),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "preview": full_content[:240] + ("..." if len(full_content) > 240 else ""),
        "full_content": full_content,
        "content_hash": content_hash
    }
        # Experimental Open Knowledge Format (OKF) v0.2 Knowledge Bundle generation
    try:
        from backend.services.okf_service import generate_okf_bundle_from_sections
        okf_res = generate_okf_bundle_from_sections(
            sections=sections,
            document_id=doc_id,
            document_name=title,
            user_id="default_user"
        )
        doc_entry["okf_bundle_id"] = okf_res.get("bundle_id")
        doc_entry["okf_concepts_count"] = okf_res.get("concept_count", 0)
    except Exception as okf_err:
        logger.warning(f"[OKF] Experimental bundle generation skipped: {okf_err}")
    indexed_documents.append(doc_entry)
    save_vector_store_to_disk()

    logger.info(f"Successfully indexed '{filename}' into {len(chunks)} structural chunks.")
    return {
        "message": f"Successfully indexed '{filename}' into {len(chunks)} structural chunks.",
        "document": doc_entry
    }

def process_custom_text(title: str, content: str) -> dict:
    clean_title = title.strip() or "Untitled Note"
    clean_content = clean_text_artifacts(content.strip())
    
    if not clean_content:
        raise HTTPException(status_code=400, detail="Notes content cannot be empty.")

    # Deduplication check
    existing_doc = find_duplicate_document(clean_content, clean_title)
    if existing_doc:
        return {
            "message": f"Notes titled '{clean_title}' are already indexed in the Knowledge Base.",
            "document": existing_doc,
            "already_indexed": True
        }

    doc_id = f"note-{len(indexed_documents) + 1}-{int(datetime.now().timestamp())}"
    content_hash = compute_content_hash(clean_content)

    sections = [{"heading": clean_title, "text": clean_content, "page_number": 1}]
    chunks = chunk_document_sections(
        sections=sections,
        document_id=doc_id,
        document_name=clean_title,
        document_type="custom_text",
        content_hash=content_hash,
        chunk_size=500,
        chunk_overlap=75
    )

    if not chunks:
        raise HTTPException(status_code=400, detail="Content was too short to generate chunks.")

    try:
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        vs_module.vector_store.add_texts(texts, metadatas=metadatas)
        hybrid_retriever.add_chunks(chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index note into vector store: {str(e)}")

    doc_entry = {
        "id": doc_id,
        "title": clean_title,
        "source_type": "custom_text",
        "document_type": "custom_text",
        "chunk_count": len(chunks),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "preview": clean_content[:240] + ("..." if len(clean_content) > 240 else ""),
        "full_content": clean_content,
        "content_hash": content_hash
    }
        # Experimental Open Knowledge Format (OKF) v0.2 Knowledge Bundle generation
    try:
        from backend.services.okf_service import generate_okf_bundle_from_sections
        okf_res = generate_okf_bundle_from_sections(
            sections=sections,
            document_id=doc_id,
            document_name=title,
            user_id="default_user"
        )
        doc_entry["okf_bundle_id"] = okf_res.get("bundle_id")
        doc_entry["okf_concepts_count"] = okf_res.get("concept_count", 0)
    except Exception as okf_err:
        logger.warning(f"[OKF] Experimental bundle generation skipped: {okf_err}")
    indexed_documents.append(doc_entry)
    save_vector_store_to_disk()

    return {
        "message": f"Successfully indexed '{clean_title}' into {len(chunks)} chunks.",
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

    clean_transcript = clean_text_artifacts(transcript)
    if not clean_transcript:
        raise HTTPException(status_code=400, detail="YouTube video had no transcript available.")

    title = custom_title.strip() if custom_title else f"YouTube Video ({video_id})"

    existing_doc = find_duplicate_document(clean_transcript, title)
    if existing_doc:
        return {
            "message": f"Transcript for '{title}' is already indexed in the Knowledge Base.",
            "document": existing_doc,
            "already_indexed": True
        }

    doc_id = f"yt-{len(indexed_documents) + 1}-{int(datetime.now().timestamp())}"
    content_hash = compute_content_hash(clean_transcript)

    sections = [{"heading": title, "text": clean_transcript, "page_number": 1}]
    chunks = chunk_document_sections(
        sections=sections,
        document_id=doc_id,
        document_name=title,
        document_type="youtube",
        content_hash=content_hash,
        chunk_size=500,
        chunk_overlap=75
    )

    if not chunks:
        raise HTTPException(status_code=400, detail="Video transcript was too short to generate chunks.")

    try:
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        vs_module.vector_store.add_texts(texts, metadatas=metadatas)
        hybrid_retriever.add_chunks(chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index YouTube transcript: {str(e)}")

    doc_entry = {
        "id": doc_id,
        "title": title,
        "source_type": "youtube",
        "document_type": "youtube",
        "chunk_count": len(chunks),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "preview": clean_transcript[:240] + ("..." if len(clean_transcript) > 240 else ""),
        "full_content": clean_transcript,
        "content_hash": content_hash
    }
        # Experimental Open Knowledge Format (OKF) v0.2 Knowledge Bundle generation
    try:
        from backend.services.okf_service import generate_okf_bundle_from_sections
        okf_res = generate_okf_bundle_from_sections(
            sections=sections,
            document_id=doc_id,
            document_name=title,
            user_id="default_user"
        )
        doc_entry["okf_bundle_id"] = okf_res.get("bundle_id")
        doc_entry["okf_concepts_count"] = okf_res.get("concept_count", 0)
    except Exception as okf_err:
        logger.warning(f"[OKF] Experimental bundle generation skipped: {okf_err}")
    indexed_documents.append(doc_entry)
    save_vector_store_to_disk()

    return {
        "message": f"Successfully indexed YouTube video into {len(chunks)} chunks.",
        "document": doc_entry
    }

def remove_document(doc_id: str) -> dict:
    """Removes a specific document by its ID and synchronizes both FAISS and BM25."""
    success = delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found.")
    hybrid_retriever.sync_from_faiss()
    return {"message": f"Document '{doc_id}' successfully removed from Knowledge Base."}
