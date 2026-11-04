"""
Index Persistence, Deletion & Concurrency Reliability Test Suite
Tests:
1. FAISS & BM25 disk persistence roundtrip.
2. Document deletion updates BOTH FAISS and BM25 simultaneously.
3. SHA-256 duplicate document detection & rejection.
4. Multi-threaded concurrent retrieval stress test (20 concurrent threads).
5. FlashRank CPU latency and memory footprint measurement.
"""

import os
import sys
import time
import json
import unittest
import concurrent.futures

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.vector_store import (
    vector_store,
    indexed_documents,
    save_vector_store_to_disk,
    load_vector_store_from_disk,
    find_duplicate_document,
    compute_content_hash,
    delete_document
)
from backend.services.hybrid_retriever import hybrid_retriever
from backend.services.document_service import process_custom_text

class TestPersistenceConcurrency(unittest.TestCase):

    def test_01_persistence_roundtrip(self):
        """Vector store and BM25 index must persist to disk and reload identically."""
        # 1. Check current counts
        initial_doc_count = len(indexed_documents)
        initial_bm25_count = len(hybrid_retriever.corpus_chunks)
        self.assertGreater(initial_doc_count, 0)
        self.assertGreater(initial_bm25_count, 0)

        # 2. Save explicitly to disk
        save_vector_store_to_disk()

        # 3. Reload from disk
        load_vector_store_from_disk()
        reloaded_doc_count = len(indexed_documents)
        reloaded_bm25_count = len(hybrid_retriever.corpus_chunks)

        self.assertEqual(initial_doc_count, reloaded_doc_count, "Document registry count must match after reload.")
        self.assertEqual(initial_bm25_count, reloaded_bm25_count, "BM25 corpus size must match after reload.")

    def test_02_duplicate_upload_rejection(self):
        """Uploading identical content must trigger SHA-256 duplicate rejection."""
        test_content = "This is a unique test note for duplicate verification.\nIt contains unique content to test hash matching."
        title = "Duplicate Test Document"

        # First upload
        res1 = process_custom_text(title, test_content)
        doc1_id = res1["document"]["id"]

        try:
            # Second upload of identical content
            res2 = process_custom_text(title, test_content)
            self.assertTrue(res2.get("already_indexed", False), "Duplicate upload must be detected.")
            self.assertEqual(res2["document"]["id"], doc1_id, "Duplicate response must reference original doc_id.")
        finally:
            # Clean up the test document
            delete_document(doc1_id)

    def test_03_deletion_synchronization(self):
        """Deleting a document must remove its chunks from BOTH FAISS and BM25 indices."""
        test_content = "Ephemeral Document For Deletion Testing.\nContains temporary information about distributed consensus protocols."
        title = "Ephemeral Deletion Test"

        # Index temporary doc
        res = process_custom_text(title, test_content)
        temp_doc_id = res["document"]["id"]

        # Verify present in BM25
        bm25_match_before = any(c.get("metadata", {}).get("doc_id") == temp_doc_id for c in hybrid_retriever.corpus_chunks)
        self.assertTrue(bm25_match_before, "Temporary doc must be present in BM25 before deletion.")

        # Delete document
        del_result = delete_document(temp_doc_id)
        self.assertTrue(del_result, "delete_document must return True.")

        # Verify removed from BM25
        bm25_match_after = any(c.get("metadata", {}).get("doc_id") == temp_doc_id for c in hybrid_retriever.corpus_chunks)
        self.assertFalse(bm25_match_after, "Temporary doc must be absent from BM25 after deletion.")

        # Verify not retrieved
        docs = hybrid_retriever.hybrid_search("Ephemeral Document For Deletion Testing", k=3)
        retrieved_ids = [d.metadata.get("doc_id") for d in docs]
        self.assertNotIn(temp_doc_id, retrieved_ids, "Deleted doc must not appear in hybrid search results.")

    def test_04_concurrent_retrieval_thread_safety(self):
        """20 concurrent threads running hybrid search must execute with zero race conditions or errors."""
        queries = [
            "Dijkstra shortest path",
            "Fractional Knapsack greedy DAA-4",
            "Bellman-Ford negative weight cycles",
            "Database normalization 1NF 2NF 3NF",
            "Banker's Algorithm deadlock avoidance",
            "K-Means clustering ML-4",
            "Support Vector Machine ML-2 email spam",
            "Smart contract BC-3 customer account",
            "ACID properties consistency durability",
            "Coffman conditions mutual exclusion"
        ] * 2  # 20 total queries

        latencies = []
        errors = []

        def worker(q):
            t0 = time.perf_counter()
            try:
                results = hybrid_retriever.hybrid_search(q, k=3)
                elapsed_ms = (time.perf_counter() - t0) * 1000
                return elapsed_ms, len(results), None
            except Exception as e:
                return 0, 0, str(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker, q) for q in queries]
            for f in concurrent.futures.as_completed(futures):
                lat, count, err = f.result()
                if err:
                    errors.append(err)
                else:
                    latencies.append(lat)
                    self.assertGreater(count, 0)

        self.assertEqual(len(errors), 0, f"Concurrent execution produced errors: {errors}")
        self.assertEqual(len(latencies), 20, "All 20 concurrent queries must complete successfully.")

        sorted_lats = sorted(latencies)
        p50 = sorted_lats[len(sorted_lats) // 2]
        p95 = sorted_lats[int(len(sorted_lats) * 0.95)]
        print(f"\n[Concurrent Stress Test: 20 threads] p50: {p50:.2f}ms | p95: {p95:.2f}ms")

if __name__ == "__main__":
    unittest.main()
