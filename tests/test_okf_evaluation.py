"""
Open Knowledge Format (OKF) v0.2 Prototype Evaluation & Comparison Benchmark.
Compares Baseline RAG vs RAG + OKF on:
1. Single-concept queries
2. Related-concept / comparison queries
3. Multi-hop queries
4. Cross-concept / cross-section queries
5. Unsupported queries
Measures retrieval latency, context richness, link traversal, and citation provenance.
"""

import unittest
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.parsers import parse_plain_or_markdown
from backend.services.okf_service import (
    generate_okf_bundle_from_sections,
    validate_okf_bundle,
    delete_bundle_for_document
)
from backend.services.okf_retriever import (
    retrieve_okf_concepts,
    format_okf_context,
    is_relational_or_multihop_query
)
from backend.services.hybrid_retriever import hybrid_retriever
from backend.services.chunking import chunk_document_sections
from backend.vector_store import vector_store


class TestOKFKnowledgeLayer(unittest.TestCase):
    """Unit tests for OKF v0.2 bundle generation, validation, and retrieval."""

    @classmethod
    def setUpClass(cls):
        cls.doc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "sample_documents", "cs_core_fundamentals.md"))
        with open(cls.doc_path, "rb") as f:
            cls.raw_bytes = f.read()

        cls.sections = parse_plain_or_markdown(cls.raw_bytes)
        cls.doc_id = "test-cs-okf-doc"
        cls.user_id = "eval_user"

        # Generate OKF Bundle
        cls.bundle = generate_okf_bundle_from_sections(
            sections=cls.sections,
            document_id=cls.doc_id,
            document_name="cs_core_fundamentals.md",
            user_id=cls.user_id
        )

        # Index chunks into hybrid retriever for comparison
        content_hash = "eval_hash_123"
        cls.chunks = chunk_document_sections(
            sections=cls.sections,
            document_id=cls.doc_id,
            document_name="cs_core_fundamentals.md",
            document_type="markdown",
            content_hash=content_hash,
            chunk_size=500,
            chunk_overlap=75
        )
        hybrid_retriever.add_chunks(cls.chunks)

    @classmethod
    def tearDownClass(cls):
        delete_bundle_for_document(cls.doc_id, user_id=cls.user_id)

    def test_bundle_conforms_to_okf_v02_spec(self):
        """Verifies bundle structure, index.md, log.md, and YAML frontmatter against OKF v0.2."""
        bundle_path = self.bundle["bundle_path"]
        val = validate_okf_bundle(bundle_path)
        self.assertTrue(val["is_valid"], f"OKF Bundle validation failed: {val['errors']}")
        self.assertEqual(len(val["errors"]), 0)
        self.assertGreaterEqual(val["concept_count"], 5)

        # Verify index.md exists
        self.assertTrue(os.path.exists(os.path.join(bundle_path, "index.md")))
        # Verify log.md exists
        self.assertTrue(os.path.exists(os.path.join(bundle_path, "log.md")))
        # Verify concepts directory exists
        self.assertTrue(os.path.isdir(os.path.join(bundle_path, "concepts")))

    def test_concept_frontmatter_fields(self):
        """Verifies that concepts contain required type, title, sources provenance, and status."""
        concepts = self.bundle["concepts"]
        for c in concepts:
            fm = c["frontmatter"]
            self.assertEqual(fm["type"], "concept")
            self.assertTrue(fm["title"])
            self.assertEqual(fm["status"], "draft")
            self.assertTrue(fm["generated"])
            self.assertFalse(fm["verified"])
            self.assertGreater(len(fm["sources"]), 0)
            self.assertEqual(fm["sources"][0]["document_id"], self.doc_id)

    def test_link_traversal_connects_related_concepts(self):
        """Verifies graph linking: Bellman-Ford concept must link to Dijkstra's Algorithm."""
        concepts = self.bundle["concepts"]
        bf_concept = next((c for c in concepts if "bellman" in c["concept_id"]), None)
        self.assertIsNotNone(bf_concept, "Bellman-Ford concept not found")
        self.assertTrue(any("dijkstra" in l for l in bf_concept["outbound_links"]))

    def test_multi_user_isolation(self):
        """Ensures that concepts generated for eval_user are NOT accessible by another user."""
        other_user_concepts = retrieve_okf_concepts(
            "Dijkstra's algorithm",
            user_id="completely_different_user",
            max_concepts=3
        )
        self.assertEqual(len(other_user_concepts), 0, "Cross-user data leakage detected!")

    def test_rag_vs_okf_benchmark_evaluation(self):
        """
        Runs the full 5-query comparative benchmark between Baseline RAG and RAG + OKF.
        Measures latency, context size, concept capture, and link traversal.
        """
        queries = [
            {
                "category": "Single-Concept",
                "query": "What is Dijkstra's algorithm and what is its optimal time complexity?",
                "expected_terms": ["dijkstra", "greedy", "shortest path"]
            },
            {
                "category": "Related-Concepts / Comparison",
                "query": "How does the Bellman-Ford algorithm differ from Dijkstra's algorithm regarding negative edge weights?",
                "expected_terms": ["bellman", "dijkstra", "negative"]
            },
            {
                "category": "Multi-Hop Traversal",
                "query": "Which algorithm can detect negative-weight cycles, and how does it relate to single-source shortest path search?",
                "expected_terms": ["negative", "cycle", "bellman"]
            },
            {
                "category": "Cross-Section / Cross-Concept",
                "query": "What deadlock conditions must hold in an operating system, and how does Dijkstra's Banker's algorithm prevent it?",
                "expected_terms": ["deadlock", "coffman", "banker"]
            },
            {
                "category": "Unsupported / Out-of-Corpus",
                "query": "What is the quantum annealing complexity of Bellman-Ford in distributed neural clusters?",
                "expected_terms": []
            }
        ]

        print("\n" + "=" * 80)
        print("OKF v0.2 EXPERIMENTAL BENCHMARK: BASELINE RAG vs. RAG + OKF")
        print("=" * 80)

        for q in queries:
            query_str = q["query"]
            cat = q["category"]

            # 1. Baseline RAG
            t0 = time.perf_counter()
            baseline_chunks = hybrid_retriever.hybrid_search(query_str, k=3)
            t_baseline = (time.perf_counter() - t0) * 1000.0
            baseline_text = " ".join(c.page_content for c in baseline_chunks)

            # 2. RAG + OKF
            t1 = time.perf_counter()
            is_rel = is_relational_or_multihop_query(query_str)
            okf_concepts = []
            if is_rel:
                okf_concepts = retrieve_okf_concepts(query_str, user_id=self.user_id, max_concepts=2, max_depth=1)
            okf_context = format_okf_context(okf_concepts)
            combined_context = f"{baseline_text}\n\n{okf_context}"
            t_okf = (time.perf_counter() - t1) * 1000.0

            print(f"\n[Category: {cat}]")
            print(f"Query: \"{query_str}\"")
            print(f" - Is Relational / Multi-hop: {is_rel}")
            print(f" - Baseline Latency: {t_baseline:.2f}ms | Chunks: {len(baseline_chunks)} | Context Chars: {len(baseline_text)}")
            print(f" - OKF Traversal Latency: {t_okf:.2f}ms | Concepts Retrieved: {len(okf_concepts)}")
            if okf_concepts:
                print(f"   * Retrieved Concepts: {[c['title'] for c in okf_concepts]}")
                for c in okf_concepts:
                    if c.get("outbound_links"):
                        print(f"   * Outbound Links Traversed: {[l['title'] for l in c['outbound_links']]}")

            # Assertions
            self.assertGreater(len(baseline_chunks), 0)
            if cat in ["Related-Concepts / Comparison", "Multi-Hop Traversal", "Cross-Section / Cross-Concept"]:
                self.assertTrue(is_rel, f"Query '{query_str}' was not classified as relational!")
                self.assertGreaterEqual(len(okf_concepts), 1, f"OKF failed to retrieve concepts for '{query_str}'")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    unittest.main()

