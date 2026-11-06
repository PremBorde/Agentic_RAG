import os
import json
import shutil
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple

import faiss
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from backend.embeddings import embeddings, safe_str, splitter

logger = logging.getLogger("agentic_studio.vector_store")

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
VECTOR_STORE_DIR = os.path.join(DATA_DIR, "vector_store")
FAISS_INDEX_DIR = os.path.join(VECTOR_STORE_DIR, "faiss_index")
REGISTRY_FILE = os.path.join(VECTOR_STORE_DIR, "documents_registry.json")

# In-memory document registry (single persistent reference)
indexed_documents: List[Dict[str, Any]] = []

def compute_content_hash(content: str) -> str:
    """Computes SHA-256 hash of text content to prevent duplicate indexing."""
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()

def create_empty_vector_store() -> FAISS:
    """Creates a blank FAISS vector store with BGE-small 384-dimensional IndexFlatL2."""
    index = faiss.IndexFlatL2(384)
    return FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={}
    )

def save_vector_store_to_disk() -> bool:
    """Persists the FAISS index and the documents registry to disk."""
    try:
        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
        # 1. Save FAISS index
        if vector_store and len(vector_store.index_to_docstore_id) > 0:
            vector_store.save_local(FAISS_INDEX_DIR)
        elif os.path.exists(FAISS_INDEX_DIR):
            shutil.rmtree(FAISS_INDEX_DIR, ignore_errors=True)

        # 2. Save document metadata registry
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(indexed_documents, f, indent=2, ensure_ascii=False)
        logger.info(f"Vector store persisted to {VECTOR_STORE_DIR} ({len(indexed_documents)} documents).")
        return True
    except Exception as e:
        logger.error(f"Failed to persist vector store to disk: {e}")
        return False

def rebuild_vector_store_from_registry(loaded_docs: List[Dict[str, Any]]) -> Tuple[FAISS, int]:
    """Reconstructs FAISS vector store from full_content preserved in registry entries."""
    vs = create_empty_vector_store()
    rebuilt_chunks = 0
    from backend.services.chunking import chunk_document_sections
    for doc in loaded_docs:
        content = doc.get("full_content", "")
        if not content:
            continue
        title = doc.get("title", "Document")
        doc_id = doc.get("id", "doc")
        doc_type = doc.get("document_type", "file")
        content_hash = doc.get("content_hash", "")
        sections = [{"heading": title, "text": content, "page_number": 1}]
        chunks = chunk_document_sections(sections, doc_id, title, doc_type, content_hash, chunk_size=500, chunk_overlap=75)
        if chunks:
            texts = [c["text"] for c in chunks]
            metadatas = [c["metadata"] for c in chunks]
            vs.add_texts(texts, metadatas=metadatas)
            rebuilt_chunks += len(chunks)
    return vs, rebuilt_chunks

def load_vector_store_from_disk() -> Tuple[FAISS, List[Dict[str, Any]]]:
    """
    Loads the persistent FAISS index and document registry from disk.
    Automatically rebuilds FAISS from registry if index files are missing or corrupted.
    """
    global indexed_documents
    loaded_docs: List[Dict[str, Any]] = []
    
    # 1. Load document registry
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                loaded_docs = json.load(f)
            logger.info(f"Loaded {len(loaded_docs)} document entries from {REGISTRY_FILE}.")
        except Exception as e:
            logger.warning(f"Corrupted registry file {REGISTRY_FILE}: {e}. Initializing empty registry.")
            loaded_docs = []

    # 2. Load FAISS index if present
    if os.path.exists(FAISS_INDEX_DIR) and os.path.exists(os.path.join(FAISS_INDEX_DIR, "index.faiss")):
        try:
            vs = FAISS.load_local(
                FAISS_INDEX_DIR,
                embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info(f"Successfully loaded persistent FAISS index with {len(vs.index_to_docstore_id)} chunks.")
            indexed_documents.clear()
            indexed_documents.extend(loaded_docs)
            return vs, loaded_docs
        except Exception as e:
            logger.error(f"Failed to load FAISS index from {FAISS_INDEX_DIR}: {e}. Attempting auto-rebuild from registry...")

    # 3. Automatic Recovery from Registry Source Content
    docs_with_content = [d for d in loaded_docs if d.get("full_content")]
    if docs_with_content:
        try:
            vs, rebuilt_chunks = rebuild_vector_store_from_registry(loaded_docs)
            if rebuilt_chunks > 0:
                logger.warning(
                    f"[RECOVERY] Rebuilt FAISS index with {rebuilt_chunks} chunks from "
                    f"{len(docs_with_content)} registry documents."
                )
                try:
                    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
                    vs.save_local(FAISS_INDEX_DIR)
                except Exception as save_err:
                    logger.error(f"[RECOVERY] Failed to persist rebuilt FAISS index: {save_err}")
                indexed_documents.clear()
                indexed_documents.extend(loaded_docs)
                return vs, loaded_docs
        except Exception as rebuild_err:
            logger.error(f"[RECOVERY] Automatic index reconstruction failed: {rebuild_err}")
    elif loaded_docs:
        logger.error(
            f"[RECOVERY FAILED] {len(loaded_docs)} documents found in registry but none contain source text. "
            f"FAISS index remains empty. Manual re-upload required."
        )

    indexed_documents.clear()
    indexed_documents.extend(loaded_docs)
    return create_empty_vector_store(), loaded_docs

# Initialize Vector Store on module load
vector_store, _ = load_vector_store_from_disk()

class UniversalHybridRetrieverWrapper:
    """LangChain-compatible wrapper that coordinates FAISS + BM25 + RRF hybrid retrieval."""
    def invoke(self, query: str, **kwargs) -> List[Any]:
        try:
            from backend.services.hybrid_retriever import hybrid_retriever
            return hybrid_retriever.invoke(query)
        except Exception as e:
            logger.warning(f"Hybrid retrieval fallback to raw FAISS: {e}")
            return vector_store.similarity_search(query, k=4)

retriever = UniversalHybridRetrieverWrapper()

def clear_vector_store():
    """Clears both the in-memory vector store and the persistent files on disk."""
    global vector_store, retriever, indexed_documents
    vector_store = create_empty_vector_store()
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})
    indexed_documents.clear()

    try:
        if os.path.exists(FAISS_INDEX_DIR):
            shutil.rmtree(FAISS_INDEX_DIR, ignore_errors=True)
        if os.path.exists(REGISTRY_FILE):
            os.remove(REGISTRY_FILE)
        logger.info("Cleared all vector store data from memory and disk.")
    except Exception as e:
        logger.error(f"Error removing vector store files: {e}")

    # Synchronize BM25 hybrid retriever
    try:
        from backend.services.hybrid_retriever import hybrid_retriever
        hybrid_retriever.clear()
    except Exception as e:
        logger.warning(f"Error clearing hybrid retriever: {e}")

    # Synchronize OKF knowledge bundle store
    try:
        from backend.services.okf_service import clear_all_bundles
        clear_all_bundles()
    except Exception as e:
        logger.warning(f"Error clearing OKF bundles: {e}")



def delete_document(doc_id: str) -> bool:
    """
    Deletes a specific document by doc_id or title from the registry and rebuilds
    the persistent vector store and BM25 index without the deleted document.
    """
    global vector_store, retriever, indexed_documents
    norm_id = str(doc_id).strip().lower()
    targets = [
        d for d in indexed_documents 
        if str(d.get("id", "")).strip().lower() == norm_id 
        or str(d.get("title", "")).strip().lower() == norm_id
    ]

    if not targets:
        return False

    for target in targets:
        t_id = target.get("id", doc_id)
        try:
            from backend.services.okf_service import delete_bundle_for_document
            delete_bundle_for_document(t_id)
        except Exception as e:
            logger.warning(f"[OKF] Failed to clean up bundle for {t_id}: {e}")

        try:
            from backend.services.hybrid_retriever import hybrid_retriever
            hybrid_retriever.remove_document(t_id)
        except Exception as e:
            logger.warning(f"Could not remove document from hybrid_retriever: {e}")

    remaining = [d for d in indexed_documents if d not in targets]
    indexed_documents.clear()
    indexed_documents.extend(remaining)

    # Reconstruct vector store from remaining documents
    new_vs = create_empty_vector_store()
    for doc in indexed_documents:
        full_content = doc.get("full_content", "")
        if full_content:
            from backend.services.chunking import chunk_document_sections
            sections = [{"heading": doc.get("title", "Document"), "text": full_content, "page_number": 1}]
            chunks = chunk_document_sections(
                sections=sections,
                document_id=doc.get("id", "doc"),
                document_name=doc.get("title", "Document"),
                document_type=doc.get("document_type", "file"),
                content_hash=doc.get("content_hash", ""),
                chunk_size=500,
                chunk_overlap=75
            )
            if chunks:
                new_vs.add_texts(
                    [c["text"] for c in chunks],
                    metadatas=[c["metadata"] for c in chunks]
                )

    vector_store = new_vs
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})
    save_vector_store_to_disk()

    return True

def find_duplicate_document(content: str, title: str) -> Optional[Dict[str, Any]]:
    """Checks if a document with identical content hash or exact title already exists."""
    content_hash = compute_content_hash(content)
    for doc in indexed_documents:
        if doc.get("content_hash") == content_hash:
            return doc
        if doc.get("title", "").strip().lower() == title.strip().lower() and abs(len(doc.get("full_content", "")) - len(content)) < 5:
            return doc
    return None

def format_docs(docs: List[Any]) -> str:
    """
    Formats retrieved document chunks with clear source provenance, section headings,
    page numbers, and chunk identifiers for unambiguous prompt grounding.
    """
    if not docs:
        return ""
    formatted_blocks = []
    for idx, doc in enumerate(docs, start=1):
        content = safe_str(getattr(doc, "page_content", doc)).strip()
        meta = getattr(doc, "metadata", {}) or {}
        src = meta.get("document_name") or meta.get("source") or "Document"
        page = meta.get("page_number")
        heading = meta.get("section_heading")
        chunk_id = meta.get("chunk_id", f"chunk-{idx}")
        
        header_parts = [f"[Chunk {idx}]"]
        header_parts.append(f"Source: {src}")
        if page:
            header_parts.append(f"Page: {page}")
        if heading and heading != "General":
            header_parts.append(f"Section: \"{heading}\"")
            
        header = " | ".join(header_parts)
        formatted_blocks.append(f"{header}\n{content}")
    return "\n\n".join(formatted_blocks)
