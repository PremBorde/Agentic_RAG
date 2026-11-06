"""
Hybrid Retrieval Engine (FAISS Dense Vector Search + BM25 Lexical Keyword Search + Optional FlashRank Reranker)
Combines dense semantic understanding with precise lexical keyword matching using
Reciprocal Rank Fusion (RRF), optional CPU-efficient reranking, and dynamic relevance filtering.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document

from backend.vector_store import vector_store, VECTOR_STORE_DIR

logger = logging.getLogger("hybrid_retriever")

BM25_STORE_FILE = os.path.join(VECTOR_STORE_DIR, "bm25_store.json")
MODELS_CACHE_DIR = os.path.join(os.path.dirname(VECTOR_STORE_DIR), "models")

def tokenize_for_bm25(text: str) -> List[str]:
    """Tokenizes text into lowercase words, preserving technical terms, alphanumeric codes, and hyphens."""
    if not text:
        return []
    tokens = re.findall(r'[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)?', text.lower())
    return tokens

class HybridRetriever:
    """
    Coordinates Dense FAISS retrieval and Lexical BM25 retrieval
    with Reciprocal Rank Fusion (RRF) and optional lightweight FlashRank reranking.
    """
    def __init__(
        self,
        k_rrf: int = 60,
        weight_dense: float = 0.55,
        weight_bm25: float = 0.45,
        enable_rerank: bool = False
    ):
        self.k_rrf = k_rrf
        self.weight_dense = weight_dense
        self.weight_bm25 = weight_bm25
        self.enable_rerank = enable_rerank
        self.corpus_chunks: List[Dict[str, Any]] = []
        self.bm25_index: Optional[BM25Okapi] = None
        self._ranker = None
        self.load_bm25_corpus()

    def get_ranker(self):
        """Lazy loader for local FlashRank TinyBERT reranker."""
        if self._ranker is None:
            try:
                from flashrank import Ranker
                os.makedirs(MODELS_CACHE_DIR, exist_ok=True)
                self._ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2", cache_dir=MODELS_CACHE_DIR)
            except Exception as e:
                logger.warning(f"Could not initialize FlashRank reranker: {e}")
                self._ranker = False
        return self._ranker if self._ranker is not False else None

    def load_bm25_corpus(self) -> None:
        """Loads persistent BM25 corpus from disk or synchronizes with FAISS docstore."""
        if os.path.exists(BM25_STORE_FILE):
            try:
                with open(BM25_STORE_FILE, "r", encoding="utf-8") as f:
                    self.corpus_chunks = json.load(f)
                tokenized_corpus = [tokenize_for_bm25(c.get("text", "")) for c in self.corpus_chunks]
                if tokenized_corpus:
                    self.bm25_index = BM25Okapi(tokenized_corpus)
                logger.info(f"Loaded {len(self.corpus_chunks)} chunks into BM25 index.")
                return
            except Exception as e:
                logger.warning(f"Failed to load BM25 store from disk: {e}. Rebuilding from FAISS.")

        self.sync_from_faiss()

    def save_bm25_corpus(self) -> None:
        """Persists BM25 corpus chunks to disk."""
        try:
            os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
            with open(BM25_STORE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.corpus_chunks, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to persist BM25 corpus: {e}")

    def sync_from_faiss(self) -> None:
        """Synchronizes BM25 corpus chunks with current FAISS docstore."""
        import backend.vector_store as vs_module
        vs = vs_module.vector_store
        chunks = []
        if vs and hasattr(vs, "docstore") and hasattr(vs.docstore, "_dict"):
            for doc_id, doc in vs.docstore._dict.items():
                content = getattr(doc, "page_content", str(doc))
                meta = getattr(doc, "metadata", {})
                chunks.append({"text": content, "metadata": meta})
        
        # If FAISS was empty but registry has documents with source text, recover BM25 chunks directly
        if not chunks:
            for doc in getattr(vs_module, "indexed_documents", []):
                content = doc.get("full_content", "")
                if content:
                    from backend.services.chunking import chunk_document_sections
                    sections = [{"heading": doc.get("title", "Document"), "text": content, "page_number": 1}]
                    doc_chunks = chunk_document_sections(sections, doc.get("id", "doc"), doc.get("title", "Document"), doc.get("document_type", "file"), doc.get("content_hash", ""), chunk_size=500, chunk_overlap=75)
                    chunks.extend(doc_chunks)

        self.corpus_chunks = chunks
        if chunks:
            tokenized = [tokenize_for_bm25(c["text"]) for c in chunks]
            self.bm25_index = BM25Okapi(tokenized)
            self.save_bm25_corpus()
            logger.info(f"[RECOVERY] BM25 corpus synchronized with {len(chunks)} chunks.")
        else:
            self.bm25_index = None

    def add_documents(self, documents: List[Document]) -> None:
        """Adds LangChain Document objects to BM25 index."""
        chunks = [{"text": doc.page_content, "metadata": doc.metadata} for doc in documents]
        self.add_chunks(chunks)

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """Adds new chunks to the BM25 index."""
        self.corpus_chunks.extend(chunks)
        tokenized = [tokenize_for_bm25(c["text"]) for c in self.corpus_chunks]
        self.bm25_index = BM25Okapi(tokenized) if tokenized else None
        self.save_bm25_corpus()

    def remove_document(self, doc_id: str) -> None:
        """Removes all chunks associated with doc_id from the BM25 index."""
        self.corpus_chunks = [
            c for c in self.corpus_chunks 
            if c.get("metadata", {}).get("doc_id") != doc_id
        ]
        if self.corpus_chunks:
            tokenized = [tokenize_for_bm25(c["text"]) for c in self.corpus_chunks]
            self.bm25_index = BM25Okapi(tokenized) if tokenized else None
        else:
            self.bm25_index = None
        self.save_bm25_corpus()

    def clear(self) -> None:
        """Clears the BM25 corpus and index."""
        self.corpus_chunks = []
        self.bm25_index = None
        if os.path.exists(BM25_STORE_FILE):
            try:
                os.remove(BM25_STORE_FILE)
            except Exception:
                pass

    def retrieve_dense(self, query: str, top_k: int = 8) -> List[Tuple[Document, float]]:
        """Performs dense vector retrieval using FAISS with L2/cosine scores."""
        import backend.vector_store as vs_module
        vs = vs_module.vector_store
        if not vs or len(vs.index_to_docstore_id) == 0:
            return []
        try:
            k_val = min(top_k, len(vs.index_to_docstore_id))
            results = vs.similarity_search_with_score(query, k=k_val)
            return results
        except Exception as e:
            logger.error(f"Dense FAISS retrieval error: {e}")
            return []

    def retrieve_bm25(self, query: str, top_k: int = 8) -> List[Tuple[Dict[str, Any], float]]:
        """Performs lexical keyword retrieval using BM25Okapi."""
        if not self.bm25_index or not self.corpus_chunks:
            return []
        q_tokens = tokenize_for_bm25(query)
        if not q_tokens:
            return []
        scores = self.bm25_index.get_scores(q_tokens)
        
        scored_chunks = []
        for idx, score in enumerate(scores):
            if score > 0:
                scored_chunks.append((self.corpus_chunks[idx], float(score)))
                
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]

    def hybrid_search(
        self,
        query: str,
        k: int = 4,
        dense_k: int = 12,
        bm25_k: int = 12,
        doc_filter: Optional[str] = None,
        doc_ids: Optional[List[str]] = None
    ) -> List[Document]:
        """
        Executes hybrid search combining FAISS dense and BM25 lexical rankings
        via Reciprocal Rank Fusion (RRF), multi-field metadata filtering, near-duplicate
        suppression, and optional lightweight reranking.
        """
        # 1. Fetch dense candidates
        dense_results = self.retrieve_dense(query, top_k=dense_k)
        # 2. Fetch BM25 candidates
        bm25_results = self.retrieve_bm25(query, top_k=bm25_k)

        # 3. Reciprocal Rank Fusion
        fusion_map: Dict[str, Dict[str, Any]] = {}

        # Add Dense Ranks
        for rank, (doc, _) in enumerate(dense_results, start=1):
            key = doc.page_content.strip()
            score_contrib = self.weight_dense * (1.0 / (self.k_rrf + rank))
            fusion_map[key] = {
                "doc": doc,
                "rrf_score": score_contrib,
                "dense_rank": rank,
                "bm25_rank": 999
            }

        # Add BM25 Ranks
        for rank, (chunk_dict, _) in enumerate(bm25_results, start=1):
            key = chunk_dict["text"].strip()
            score_contrib = self.weight_bm25 * (1.0 / (self.k_rrf + rank))
            if key in fusion_map:
                fusion_map[key]["rrf_score"] += score_contrib
                fusion_map[key]["bm25_rank"] = rank
            else:
                doc = Document(page_content=chunk_dict["text"], metadata=chunk_dict.get("metadata", {}))
                fusion_map[key] = {
                    "doc": doc,
                    "rrf_score": score_contrib,
                    "dense_rank": 999,
                    "bm25_rank": rank
                }

        if not fusion_map:
            return []

        ranked_candidates = list(fusion_map.values())

        # 4. Multi-field document filtering (explicit doc_ids list or doc_filter title/substring)
        if doc_ids:
            target_ids = set(str(did).strip().lower() for did in doc_ids)
            filtered = []
            for item in ranked_candidates:
                m = item["doc"].metadata or {}
                m_id = str(m.get("doc_id", "")).lower()
                m_src = str(m.get("source", "")).lower()
                m_name = str(m.get("document_name", "")).lower()
                if m_id in target_ids or any(tid in m_src or tid in m_name for tid in target_ids):
                    filtered.append(item)
            if filtered:
                ranked_candidates = filtered

        elif doc_filter:
            fl = doc_filter.strip().lower()
            filtered = []
            for item in ranked_candidates:
                m = item["doc"].metadata or {}
                m_src = str(m.get("source", "")).lower()
                m_name = str(m.get("document_name", "")).lower()
                m_id = str(m.get("doc_id", "")).lower()
                if fl in m_src or fl in m_name or fl in m_id:
                    filtered.append(item)
            if filtered:
                ranked_candidates = filtered

        # 5. Sort by combined RRF score
        ranked_candidates.sort(key=lambda x: x["rrf_score"], reverse=True)

        # 6. Near-duplicate chunk suppression to ensure context diversity
        deduped_candidates: List[Document] = []
        seen_texts: List[str] = []

        for item in ranked_candidates:
            c_doc = item["doc"]
            c_text = c_doc.page_content.strip()
            # Fast duplicate / high overlap suppression
            is_dup = False
            for prev in seen_texts:
                if c_text == prev or (len(c_text) > 80 and len(prev) > 80 and (c_text[:120] in prev or prev[:120] in c_text)):
                    is_dup = True
                    break
            if not is_dup:
                # Attach RRF score to metadata for auditability
                c_doc.metadata["rrf_score"] = float(item["rrf_score"])
                deduped_candidates.append(c_doc)
                seen_texts.append(c_text)
                if len(deduped_candidates) >= max(k * 2, 8):
                    break

        top_candidates = deduped_candidates[:max(k * 2, 8)]

        # 7. Optional FlashRank reranking
        if self.enable_rerank and len(top_candidates) > 1:
            ranker = self.get_ranker()
            if ranker:
                try:
                    from flashrank import RerankRequest
                    passages = [
                        {"id": i, "text": d.page_content, "meta": d.metadata}
                        for i, d in enumerate(top_candidates)
                    ]
                    rerank_req = RerankRequest(query=query, passages=passages)
                    reranked = ranker.rerank(rerank_req)
                    
                    id_to_doc = {i: d for i, d in enumerate(top_candidates)}
                    reranked_docs = []
                    for item in reranked:
                        doc = id_to_doc.get(item["id"])
                        if doc:
                            doc.metadata["rerank_score"] = float(item.get("score", 0.0))
                            reranked_docs.append(doc)
                    return reranked_docs[:k]
                except Exception as e:
                    logger.warning(f"Reranking failed, using RRF order: {e}")

        return top_candidates[:k]

    def invoke(self, query: str) -> List[Document]:
        """LangChain-compatible retriever interface."""
        return self.hybrid_search(query, k=4)

# Global hybrid retriever instance
hybrid_retriever = HybridRetriever()

def determine_retrieval_k(query: str, default_k: int = 4) -> int:
    """
    Dynamically resolves the optimal number of chunks k based on query complexity:
    - Comparative, cross-document, or multi-hop synthesis: k=6 to 8
    - Comprehensive summary or extraction: k=6
    - Focused single-fact lookup: k=4
    """
    q_low = query.lower().strip()
    # Comparative & multi-hop indicators
    if any(m in q_low for m in [
        "compare", "comparison", "difference between", "differences between",
        "differ from", "versus", " vs ", " vs. ", "contrast", "across documents",
        "connect", "relationship between", "how do .* and .* relate", "multi-hop"
    ]):
        return 6

    # Summarization & broad coverage indicators
    if any(m in q_low for m in [
        "summarize", "summary", "overview", "all key points", "key takeaways",
        "comprehensive", "outline all", "extract all"
    ]):
        return 6

    # Long or multi-sentence questions
    if len(query.split()) > 18:
        return 6

    return default_k

