"""
Offline unit test suite for LLM latency, quota consumption, retry semantics,
and structured conversation-history compression.
IMPORTANT: Runs 100% locally with mocks - strictly NO external Gemini API calls.
"""

import unittest
from unittest.mock import MagicMock, patch
import asyncio

from backend.memory import (
    get_thread_context_str,
    compress_assistant_turn,
    thread_histories
)
from backend.utils.retry import is_quota_exhausted_error, is_retryable_llm_error, astream_with_backoff
from backend.services.router import classify_query, QueryIntent


class TestLatencyAndQuotaAudit(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        thread_histories.clear()

    def test_01_conversation_history_structured_compression(self):
        """Verify assistant turns are structured and bounded to save prompt quota."""
        thread_id = "test_thread_quota"
        thread_histories[thread_id] = [
            {"role": "user", "content": "Explain Dijkstra algorithm."},
            {"role": "assistant", "content": "### Dijkstra Shortest Path\n" + ("A" * 3000)},
            {"role": "user", "content": "What about its time complexity?"},
            {"role": "assistant", "content": "### Complexity Analysis\n" + ("B" * 2500)},
        ]

        context_str = get_thread_context_str(thread_id, max_turns=4, max_assistant_chars=350)

        # User queries must be preserved in full
        self.assertIn("User: Explain Dijkstra algorithm.", context_str)
        self.assertIn("User: What about its time complexity?", context_str)

        lines = context_str.split("\n")
        asst_lines = [l for l in lines if l.startswith("Assistant:")]
        self.assertEqual(len(asst_lines), 2)
        # Older assistant turn: bounded near max_assistant_chars (350)
        self.assertLessEqual(len(asst_lines[0]), 380)
        # Most recent assistant turn: bounded near 2x budget (700)
        self.assertLessEqual(len(asst_lines[1]), 750)

    def test_02_quota_error_detection_and_fast_fail(self):
        """Verify 429 / resource exhaustion errors are recognized as non-retryable to prevent burning quota."""
        quota_err = Exception("429 Resource has been exhausted (e.g. check quota).")
        self.assertTrue(is_quota_exhausted_error(quota_err))
        self.assertFalse(is_retryable_llm_error(quota_err))

        transient_err = Exception("503 Server Unavailable or Overloaded.")
        self.assertFalse(is_quota_exhausted_error(transient_err))
        self.assertTrue(is_retryable_llm_error(transient_err))

    async def test_03_astream_partial_yield_protection(self):
        """Verify that if tokens were partially yielded, retry is aborted to prevent duplicate output."""
        class MockFailingLLM:
            def __init__(self):
                self.model = "gemini-2.5-flash"
                self.call_count = 0

            async def astream(self, prompt_val):
                self.call_count += 1
                yield MagicMock(content="First partial token ")
                # Simulate mid-stream network drop
                raise ConnectionResetError("Connection dropped by peer mid-stream")

        mock_llm = MockFailingLLM()
        tokens = []

        with self.assertRaises(ConnectionResetError):
            async for chunk in astream_with_backoff(mock_llm, "test prompt", max_retries=2, allow_fallback=True):
                tokens.append(chunk.content)

        # Exactly 1 attempt should have executed: must NOT re-stream from beginning when tokens were already yielded
        self.assertEqual(mock_llm.call_count, 1)
        self.assertEqual(tokens, ["First partial token "])

    async def test_04_astream_quota_exhaustion_no_retry(self):
        """Verify that hard quota errors do NOT retry or attempt fallbacks, failing immediately."""
        class MockQuotaLLM:
            def __init__(self):
                self.model = "gemini-2.5-flash"
                self.call_count = 0

            async def astream(self, prompt_val):
                self.call_count += 1
                if True:
                    raise Exception("429 RESOURCE_EXHAUSTED: Daily quota reached")
                yield MagicMock(content="")

        mock_llm = MockQuotaLLM()

        with self.assertRaises(Exception) as ctx:
            async for _ in astream_with_backoff(mock_llm, "test prompt", max_retries=2, allow_fallback=True):
                pass

        self.assertIn("RESOURCE_EXHAUSTED", str(ctx.exception))
        # Must execute only once without retrying
        self.assertEqual(mock_llm.call_count, 1)

    def test_05_general_chat_bypasses_rag_tools(self):
        """Verify general knowledge queries and greetings bypass FAISS, BM25, and OKF completely."""
        dec_hello = classify_query("Hello there", doc_count=5)
        self.assertEqual(dec_hello.intent, QueryIntent.CONVERSATIONAL)
        self.assertFalse(dec_hello.rag_invoked)
        self.assertEqual(dec_hello.tools_selected, [])

        dec_gk = classify_query("Why is the sky blue?", doc_count=5)
        self.assertEqual(dec_gk.intent, QueryIntent.GENERAL_KNOWLEDGE)
        self.assertFalse(dec_gk.rag_invoked)
        self.assertEqual(dec_gk.tools_selected, [])

        dec_img = classify_query("Show me img of Mortal", doc_count=5)
        self.assertEqual(dec_img.intent, QueryIntent.IMAGE_SEARCH)
        self.assertFalse(dec_img.rag_invoked)
        self.assertEqual(dec_img.tools_selected, ["image_search"])

    def test_06_multi_turn_ordinal_reference_preservation(self):
        """
        Verify that numbered options (1., 2., 3.) are preserved in structured compression
        so follow-up ordinal questions ('What was the second option?') retain grounding.
        """
        thread_id = "test_ordinal_ref"
        response = (
            "### Shortest Path Algorithms\n"
            "Here are the primary algorithms for graph shortest paths:\n"
            "1. Dijkstra Algorithm: Best for non-negative edge weights.\n"
            "2. Bellman-Ford Algorithm: Capable of handling negative edge weights.\n"
            "3. Floyd-Warshall Algorithm: All-pairs shortest path computation.\n"
            "\n" + ("Additional filler explanation of path relaxation. " * 30) + "\n"
            "**Recommendation:** Use Dijkstra for single-source queries."
        )
        thread_histories[thread_id] = [
            {"role": "user", "content": "What algorithms solve shortest path?"},
            {"role": "assistant", "content": response},
        ]

        context = get_thread_context_str(thread_id, max_turns=2)
        # Must preserve option 2 entity and description
        self.assertIn("Bellman-Ford", context)
        self.assertIn("Dijkstra", context)
        self.assertIn("Recommendation:", context)

    def test_07_pronoun_reference_preservation(self):
        """
        Verify that complexity formulas and key entities are retained so pronoun questions
        ('Why does it have O(VE) complexity?') resolve unambiguously.
        """
        thread_id = "test_pronoun_ref"
        response = (
            "### Bellman-Ford Details\n"
            "Bellman-Ford relaxes all edges |V| - 1 times.\n"
            "1. Complexity: Runs in O(VE) time complexity because every edge is relaxed V times.\n"
            "2. Negative Cycles: Detects negative weight cycles on the V-th iteration.\n"
            "\n" + ("Detailed code walkthrough and edge trace. " * 25) + "\n"
            "**Key Takeaway:** O(VE) is slower than Dijkstra but detects negative cycles."
        )
        thread_histories[thread_id] = [
            {"role": "user", "content": "Explain Bellman Ford algorithm."},
            {"role": "assistant", "content": response},
        ]

        context = get_thread_context_str(thread_id, max_turns=2)
        self.assertIn("O(VE)", context)
        self.assertIn("Bellman-Ford", context)
        self.assertIn("Key Takeaway:", context)

    def test_08_topic_change_across_turns(self):
        """
        Verify topic shifts across turns (Turn 1: DAA algorithms -> Turn 2: Database indexing).
        Both topics should remain distinct and preserved without crosstalk.
        """
        thread_id = "test_topic_shift"
        thread_histories[thread_id] = [
            {"role": "user", "content": "What is 0/1 Knapsack dynamic programming?"},
            {"role": "assistant", "content": "### 0/1 Knapsack\nSolves knapsack problem using a 2D table.\n1. State: dp[i][w]\n2. Complexity: O(nW) pseudo-polynomial time.\n**Conclusion:** Use DP when weights are integers."},
            {"role": "user", "content": "Now switch topics. How does a B-Tree index work in PostgreSQL?"},
            {"role": "assistant", "content": "### PostgreSQL B-Tree Index\nB-Trees provide balanced search trees for range scans.\n1. Structure: Balanced multi-way search tree with root, branch, and leaf pages.\n2. Lookup: O(log N) search and insertion time.\n**Recommendation:** Use B-Tree for equality and range filters."},
        ]

        context = get_thread_context_str(thread_id, max_turns=4)
        # Turn 1 content preserved
        self.assertIn("0/1 Knapsack", context)
        self.assertIn("O(nW)", context)
        # Turn 2 content preserved
        self.assertIn("PostgreSQL B-Tree", context)
        self.assertIn("O(log N)", context)
        # User prompts intact
        self.assertIn("User: What is 0/1 Knapsack dynamic programming?", context)
        self.assertIn("User: Now switch topics. How does a B-Tree index work in PostgreSQL?", context)

    def test_09_long_assistant_response_priority_budgeting(self):
        """
        Verify that a massive 5,000+ character assistant response is compressed
        such that the topic, top numbered options, and decision blocks are prioritized
        and the final character length strictly adheres to budget bounds.
        """
        long_response = (
            "### Comprehensive Cloud Database Comparison\n"
            "Detailed architectural review of distributed persistence solutions across availability zones.\n"
            "1. Amazon DynamoDB: Serverless single-digit millisecond latency key-value store.\n"
            "2. Google Cloud Spanner: Globally distributed database with external consistency.\n"
            "3. Azure Cosmos DB: Multi-model globally replicated distributed NoSQL database.\n"
            "4. MongoDB Atlas: Document-oriented database with flexible JSON schemas.\n"
            "5. CockroachDB: Distributed SQL with serializable transaction isolation.\n"
            "\n" + ("Extensive benchmark tables, network topology diagrams, and IOPS numbers. " * 80) + "\n"
            "**Final Verdict:** Select Cloud Spanner if global multi-region consistency is required; otherwise DynamoDB."
        )

        # Test compression on older turn (budget 350)
        older_compact = compress_assistant_turn(long_response, max_chars=350, is_most_recent=False)
        self.assertLessEqual(len(older_compact), 350)
        self.assertIn("Cloud Database Comparison", older_compact)
        self.assertIn("1. Amazon DynamoDB", older_compact)
        self.assertIn("Final Verdict:", older_compact)

        # Test compression on recent turn (budget 700)
        recent_compact = compress_assistant_turn(long_response, max_chars=350, is_most_recent=True)
        self.assertLessEqual(len(recent_compact), 700)
        self.assertIn("Cloud Database Comparison", recent_compact)
        self.assertIn("Amazon DynamoDB", recent_compact)
        self.assertIn("Google Cloud Spanner", recent_compact)
        self.assertIn("Final Verdict:", recent_compact)

    def test_10_zero_gemini_calls_during_compression(self):
        """Verify that running conversation context compression makes strictly 0 LLM or network calls."""
        thread_id = "test_zero_calls"
        thread_histories[thread_id] = [
            {"role": "user", "content": "Test query 1"},
            {"role": "assistant", "content": "### Response 1\n" + ("Word " * 200) + "\n**Decision:** Keep local."},
            {"role": "user", "content": "Test query 2"},
            {"role": "assistant", "content": "### Response 2\n" + ("Word " * 300) + "\n**Decision:** Fast finish."},
        ]

        with patch("google.genai.Client") as mock_client:
            context = get_thread_context_str(thread_id, max_turns=4)
            # Ensure no client or API method was ever called
            self.assertEqual(mock_client.call_count, 0)
            self.assertIn("Response 1", context)
            self.assertIn("Response 2", context)


if __name__ == "__main__":
    unittest.main()
