import unittest
import os
import shutil
from fastapi.testclient import TestClient

from server import app
from backend.vector_store import (
    indexed_documents,
    clear_vector_store,
    delete_document,
    load_vector_store_from_disk,
    REGISTRY_FILE,
    FAISS_INDEX_DIR
)
from backend.services.document_service import process_custom_text, remove_document
from backend.services.hybrid_retriever import hybrid_retriever

client = TestClient(app)

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test_doc_backup")

class TestDocumentDeletion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Back up registry and FAISS index if they exist
        os.makedirs(BACKUP_DIR, exist_ok=True)
        cls.had_registry = os.path.exists(REGISTRY_FILE)
        if cls.had_registry:
            shutil.copy2(REGISTRY_FILE, os.path.join(BACKUP_DIR, "documents_registry.json"))
        cls.had_faiss = os.path.exists(FAISS_INDEX_DIR)
        if cls.had_faiss:
            shutil.copytree(FAISS_INDEX_DIR, os.path.join(BACKUP_DIR, "faiss_index"), dirs_exist_ok=True)
        cls.saved_docs = list(indexed_documents)

    @classmethod
    def tearDownClass(cls):
        # Restore original state
        clear_vector_store()
        if cls.had_registry:
            src = os.path.join(BACKUP_DIR, "documents_registry.json")
            if os.path.exists(src):
                shutil.copy2(src, REGISTRY_FILE)
        if cls.had_faiss:
            src = os.path.join(BACKUP_DIR, "faiss_index")
            if os.path.exists(src):
                shutil.copytree(src, FAISS_INDEX_DIR, dirs_exist_ok=True)
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR, ignore_errors=True)
        load_vector_store_from_disk()

    def setUp(self):
        clear_vector_store()

    def test_single_document_deletion_by_id(self):
        # Add two test notes
        doc1 = process_custom_text("Note Alpha", "This is alpha content about dynamic programming.")["document"]
        doc2 = process_custom_text("Note Beta", "This is beta content about binary search trees.")["document"]

        self.assertEqual(len(indexed_documents), 2)
        doc1_id = doc1["id"]
        doc2_id = doc2["id"]

        # Delete doc1 by id
        success = delete_document(doc1_id)
        self.assertTrue(success)
        self.assertEqual(len(indexed_documents), 1)
        self.assertEqual(indexed_documents[0]["id"], doc2_id)

        # Deleting non-existent document returns False
        self.assertFalse(delete_document("non-existent-id"))

    def test_single_document_deletion_by_title(self):
        doc1 = process_custom_text("Unique Title To Remove", "Content here for removal by title.")["document"]
        self.assertEqual(len(indexed_documents), 1)

        # Delete by title
        success = delete_document("Unique Title To Remove")
        self.assertTrue(success)
        self.assertEqual(len(indexed_documents), 0)

    def test_api_delete_document_by_id(self):
        doc1 = process_custom_text("API Test Doc", "Testing FastAPI DELETE route.")["document"]
        doc_id = doc1["id"]

        # Call DELETE /api/documents/{doc_id}
        resp = client.delete(f"/api/documents/{doc_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("successfully removed", resp.json()["message"])

        # Subsequent delete returns 404
        resp404 = client.delete(f"/api/documents/{doc_id}")
        self.assertEqual(resp404.status_code, 404)

    def test_api_clear_documents_delete_and_post(self):
        process_custom_text("Clear Test 1", "Content 1")
        process_custom_text("Clear Test 2", "Content 2")
        self.assertEqual(len(indexed_documents), 2)

        # Test DELETE /api/documents/clear
        resp_del = client.delete("/api/documents/clear")
        self.assertEqual(resp_del.status_code, 200)
        self.assertEqual(len(indexed_documents), 0)

        # Add more and test POST /api/documents/clear
        process_custom_text("Clear Test 3", "Content 3")
        self.assertEqual(len(indexed_documents), 1)

        resp_post = client.post("/api/documents/clear")
        self.assertEqual(resp_post.status_code, 200)
        self.assertEqual(len(indexed_documents), 0)

    def test_hybrid_retriever_sync_on_deletion(self):
        process_custom_text("Algorithms Guide", "Divide and conquer algorithms solve subproblems recursively.")
        self.assertEqual(len(indexed_documents), 1)
        doc_id = indexed_documents[0]["id"]

        # Check BM25 chunks
        self.assertTrue(len(hybrid_retriever.corpus_chunks) > 0)

        # Remove document
        remove_document(doc_id)
        self.assertEqual(len(indexed_documents), 0)
        # Verify BM25 corpus cleaned up
        matching_chunks = [c for c in hybrid_retriever.corpus_chunks if c.get("metadata", {}).get("document_id") == doc_id]
        self.assertEqual(len(matching_chunks), 0)

if __name__ == "__main__":
    unittest.main()
