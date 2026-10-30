import os
import json
import shutil
import hashlib
import logging
from typing import List, Dict, Any, Optional

import faiss
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from backend.embeddings import embeddings, safe_str, splitter

logger = logging.getLogger("agentic_studio.vector_store")

VECTOR_STORE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vector_store")
FAISS_INDEX_DIR = os.path.join(VECTOR_STORE_DIR, "faiss_index")
REGISTRY_FILE = os.path.join(VECTOR_STORE_DIR, "documents_registry.json")

# In-memory document registry
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

def load_vector_store_from_disk() -> tuple[FAISS, List[Dict[str, Any]]]:
    """
    Loads the persistent FAISS index and document registry from disk.
    Gracefully falls back to an empty vector store if files are missing or corrupted.
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

    # 2. Load FAISS index
    if os.path.exists(FAISS_INDEX_DIR) and os.path.exists(os.path.join(FAISS_INDEX_DIR, "index.faiss")):
        try:
            vs = FAISS.load_local(
                FAISS_INDEX_DIR,
                embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info(f"Successfully loaded persistent FAISS index with {len(vs.index_to_docstore_id)} chunks.")
            indexed_documents = loaded_docs
            return vs, loaded_docs
        except Exception as e:
            logger.error(f"Failed to load FAISS index from {FAISS_INDEX_DIR}: {e}. Creating fresh vector store.")
    
    indexed_documents = []
    return create_empty_vector_store(), []

# Initialize Vector Store on module load
vector_store, indexed_documents = load_vector_store_from_disk()
retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})

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

def delete_document(doc_id: str) -> bool:
    """
    Deletes a specific document by doc_id from the registry and rebuilds
    the persistent vector store without the deleted document.
    """
    global vector_store, retriever, indexed_documents
    initial_count = len(indexed_documents)
    indexed_documents = [d for d in indexed_documents if d.get("id") != doc_id]
    
    if len(indexed_documents) == initial_count:
        return False  # Document not found

    # Reconstruct vector store from remaining documents
    new_vs = create_empty_vector_store()
    for doc in indexed_documents:
        full_content = doc.get("full_content", "")
        if full_content:
            chunks = splitter.split_text(full_content)
            if chunks:
                new_vs.add_texts(
                    chunks,
                    metadatas=[{"source": doc.get("title", "Document"), "doc_id": doc.get("id")}] * len(chunks)
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

def format_docs(docs):
    """Formats retrieved document chunks for prompt context."""
    return "\n\n".join(safe_str(getattr(doc, "page_content", doc)) for doc in docs)
