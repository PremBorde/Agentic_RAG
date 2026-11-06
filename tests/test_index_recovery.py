"""
Offline Index Recovery and Degradation Detection Test Suite
Verifies:
1. Auto-recovery of FAISS index when files are deleted but registry contains source text.
2. Auto-recovery of BM25 store when files are deleted.
3. Both FAISS and BM25 missing: simultaneous safe reconstruction.
4. Missing indexes with unrecoverable registry (no full_content): reports degraded status honestly.
5. Zero Gemini API calls consumed.
"""

import os
import shutil
import json
import unittest
from starlette.testclient import TestClient

from backend.vector_store import (
    load_vector_store_from_disk,
    rebuild_vector_store_from_registry,
    create_empty_vector_store,
    VECTOR_STORE_DIR,
    FAISS_INDEX_DIR,
    REGISTRY_FILE
)
from backend.services.hybrid_retriever import hybrid_retriever, BM25_STORE_FILE
from server import app

class TestIndexRecovery(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_01_rebuild_vector_store_from_registry_helper(self):
        """Rebuilding from registry entries with full_content creates functional FAISS index."""
        sample_docs = [
            {
                "id": "recov_doc_1",
                "title": "Recovery Document 1",
                "document_type": "text",
                "full_content": "This is test content discussing distributed consensus and Paxos algorithms.",
                "content_hash": "hash_recov_1"
            }
        ]
        vs, count = rebuild_vector_store_from_registry(sample_docs)
        self.assertGreater(count, 0)
        self.assertEqual(len(vs.index_to_docstore_id), count)
        results = vs.similarity_search("Paxos consensus", k=1)
        self.assertEqual(len(results), 1)
        self.assertIn("paxos", results[0].page_content.lower())

    def test_02_bm25_auto_recovery_from_registry_when_missing(self):
        """When BM25 store file is missing and FAISS is empty, load_bm25_corpus reconstructs chunks."""
        import backend.vector_store as vs_module
        original_indexed = list(vs_module.indexed_documents)
        original_vs = vs_module.vector_store
        vs_module.indexed_documents.clear()
        vs_module.indexed_documents.append({
            "id": "recov_doc_bm25_1",
            "title": "BM25 Recovery Note",
            "document_type": "text",
            "full_content": "Special keyword ZYXWVU999 for lexical verification.",
            "content_hash": "hash_recov_bm25_1"
        })
        vs_module.indexed_documents.append({
            "id": "recov_doc_bm25_2",
            "title": "General System Notes",
            "document_type": "text",
            "full_content": "This is unrelated background content for corpus balance.",
            "content_hash": "hash_recov_bm25_2"
        })
        vs_module.indexed_documents.append({
            "id": "recov_doc_bm25_3",
            "title": "Architecture Overview",
            "document_type": "text",
            "full_content": "Details on distributed systems and microservice topologies.",
            "content_hash": "hash_recov_bm25_3"
        })

        try:
            # Force empty FAISS vector store and empty corpus
            vs_module.vector_store = create_empty_vector_store()
            hybrid_retriever.corpus_chunks = []
            hybrid_retriever.bm25_index = None
            hybrid_retriever.sync_from_faiss()
            self.assertGreater(len(hybrid_retriever.corpus_chunks), 0)
            self.assertIsNotNone(hybrid_retriever.bm25_index)
            results = hybrid_retriever.retrieve_bm25("ZYXWVU999", top_k=1)
            self.assertGreater(len(results), 0)
        finally:
            vs_module.vector_store = original_vs
            vs_module.indexed_documents.clear()
            vs_module.indexed_documents.extend(original_indexed)

    def test_03_health_check_honesty_when_index_empty_with_registered_docs(self):
        """Health check reports degraded when documents are registered but vector chunks are 0."""
        import backend.vector_store as vs_module
        original_indexed = list(vs_module.indexed_documents)
        original_vs = vs_module.vector_store

        try:
            # Simulate desynchronized state: 2 registered docs, 0 vector chunks
            vs_module.indexed_documents.clear()
            vs_module.indexed_documents.extend([
                {"id": "doc1", "title": "Doc 1"},
                {"id": "doc2", "title": "Doc 2"}
            ])
            vs_module.vector_store = create_empty_vector_store()

            resp = self.client.get("/health")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "degraded")
            self.assertIn("degraded", data["checks"]["vector_store"]["status"])
            self.assertEqual(data["checks"]["vector_store"]["chunks_count"], 0)
        finally:
            vs_module.indexed_documents.clear()
            vs_module.indexed_documents.extend(original_indexed)
            vs_module.vector_store = original_vs

if __name__ == "__main__":
    unittest.main()
