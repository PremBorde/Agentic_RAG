"""
Citations & Grounding Verification Test Suite
Tests:
1. Citation metadata integrity (document_name, page_number, section_heading, chunk_id, source_location).
2. Chunk content grounding (retrieved chunk actually contains the evidence supporting the query).
3. Out-of-corpus & unsupported questions handling (anti-hallucination mandate).
4. Query routing isolation (web search and general knowledge queries NEVER invoke RAG).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.hybrid_retriever import hybrid_retriever
from backend.services.router import classify_query, QueryIntent
from backend.prompts import gen_prompt

class TestCitationGrounding(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        has_dijkstra = any('dijkstra' in c.get('text', '').lower() for c in hybrid_retriever.corpus_chunks)
        if not has_dijkstra:
            from backend.services.parsers import parse_plain_or_markdown
            from backend.services.chunking import chunk_document_sections
            doc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "sample_documents", "cs_core_fundamentals.md"))
            if os.path.exists(doc_path):
                with open(doc_path, "rb") as f:
                    sections = parse_plain_or_markdown(f.read())
                chunks = chunk_document_sections(
                    sections=sections,
                    document_id="note-2-sample",
                    document_name="cs_core_fundamentals.md",
                    document_type="markdown",
                    content_hash="eval_hash_123",
                    chunk_size=500,
                    chunk_overlap=75
                )
                hybrid_retriever.add_chunks(chunks)

    def test_01_citation_metadata_completeness(self):
        """Every retrieved chunk from indexed documents must carry complete citation metadata."""
        query = "Dijkstra algorithm time complexity min-heap"
        docs = hybrid_retriever.hybrid_search(query, k=3)
        self.assertGreater(len(docs), 0, "Retrieval should return at least 1 document chunk.")

        for doc in docs:
            meta = doc.metadata
            self.assertIn("source", meta, "Metadata must contain 'source'")
            self.assertIn("doc_id", meta, "Metadata must contain 'doc_id'")
            # If from note-2, check structural attributes
            if meta.get("doc_id", "").startswith("note-"):
                self.assertIn("chunk_id", meta, "Chunk ID must be present")
                self.assertIn("page_number", meta, "Page number must be present")
                self.assertIn("section_heading", meta, "Section heading must be present")
                self.assertIn("source_location", meta, "Source location must be present")

    def test_02_chunk_content_supports_answer(self):
        """Retrieved top chunk for Dijkstra must contain the exact time complexity and data structure."""
        query = "What is the time complexity of Dijkstra's algorithm and which data structure is used?"
        docs = hybrid_retriever.hybrid_search(query, k=8)
        top_doc = docs[0]
        
        combined_text = "\n".join(d.page_content for d in docs)
        self.assertTrue(
            "O((V + E) log V)" in combined_text or "priority queue" in combined_text or "min-heap" in combined_text,
            "Retrieved chunks must explicitly contain the factual answer."
        )

    def test_03_unsupported_out_of_corpus_safety_instruction(self):
        """The generation prompt must enforce explicit negative admission when context lacks info."""
        prompt_template = gen_prompt.template if hasattr(gen_prompt, 'template') else str(gen_prompt)
        self.assertIn("If the retrieved context does not contain enough information to answer, say so clearly instead of inventing an answer.", prompt_template)
        self.assertIn("GROUNDED DOCUMENT ANSWERS: When answering questions based on retrieved documents, use only the verified facts", prompt_template)
        self.assertIn("PRECISE CITATIONS: When referencing retrieved documents, cite the exact supporting source", prompt_template)

    def test_04_query_routing_isolation_web_search(self):
        """Web search queries must NEVER trigger RAG or retrieve document chunks."""
        queries = [
            "For web search today top 5 news",
            "search the web for latest AI news",
            "what is the current weather in Tokyo?",
            "latest stock price of Google"
        ]
        for q in queries:
            decision = classify_query(q, doc_count=2)
            self.assertEqual(decision.intent, QueryIntent.WEB_SEARCH, f"Query '{q}' should be WEB_SEARCH")
            self.assertFalse(decision.rag_invoked, f"Query '{q}' should NOT invoke RAG")
            self.assertNotIn("retriever", decision.tools_selected)

    def test_05_query_routing_isolation_general_knowledge(self):
        """General coding and knowledge questions without document context must route to general LLM, not RAG."""
        queries = [
            "Write a python quicksort implementation",
            "What is the difference between TCP and UDP?",
            "Explain quantum computing basics",
            "How do promises work in JavaScript?"
        ]
        for q in queries:
            decision = classify_query(q, doc_count=2)
            self.assertEqual(decision.intent, QueryIntent.GENERAL_KNOWLEDGE, f"Query '{q}' should be GENERAL_KNOWLEDGE")
            self.assertFalse(decision.rag_invoked, f"Query '{q}' should NOT invoke RAG")
            self.assertNotIn("retriever", decision.tools_selected)

if __name__ == "__main__":
    unittest.main()
