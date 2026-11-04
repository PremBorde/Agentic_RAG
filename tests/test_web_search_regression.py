"""
Web Search Reliability & Execution Regression Test Suite.
Verifies:
1. "Latest news from this week" triggers WEB_SEARCH intent immediately.
2. "Give me news from the recent week" extracts the correct timeframe ('w' -> last 7 days).
3. "Search and send me the answer" executes a previously pending search without another acknowledgement.
4. Successful search returns structured headlines, summaries, sources, dates, and URLs to the caller.
5. Provider failure produces an honest error and never claims a search succeeded or fabricates news.
6. General knowledge questions route to general LLM and do NOT invoke web search.

STRICT MANDATE:
- Zero Gemini API calls.
- Zero external network requests during unit testing.
"""

import os
import sys
import unittest
import asyncio
import uuid
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.router import classify_query, QueryIntent
from backend.tools import is_explicit_web_search, extract_web_search_query_and_timeframe, is_web_search_continuation
from backend.services.web_search_service import (
    clean_source_domain,
    get_timeframe_label,
    search_web_structured,
    search_web_structured_async,
    format_web_search_context
)


class TestWebSearchRegression(unittest.TestCase):

    def test_01_latest_news_this_week_triggers_web_search(self):
        """1. 'Latest news from this week' triggers WEB_SEARCH immediately without RAG or general fallback."""
        query = "Latest news from this week"
        decision = classify_query(query, doc_count=3)
        
        self.assertEqual(decision.intent, QueryIntent.WEB_SEARCH)
        self.assertFalse(decision.rag_invoked)
        self.assertIn("web_search", decision.tools_selected)
        self.assertEqual(decision.selected_path, "web_search")
        self.assertIn("query", decision.params)
        self.assertEqual(decision.params.get("timeframe"), "w")

    def test_02_news_from_recent_week_resolves_timeframe(self):
        """2. 'Give me news from the recent week' resolves the correct timeframe ('w' = last 7 days)."""
        query = "Give me news from the recent week"
        self.assertTrue(is_explicit_web_search(query), "Query should be recognized as explicit web search")
        
        clean_q, tf = extract_web_search_query_and_timeframe(query)
        self.assertEqual(tf, "w", "Timeframe for 'recent week' must resolve to 'w' (last 7 days)")
        self.assertEqual(clean_q.lower(), "news")

        # Also verify decision parameters from router
        decision = classify_query(query, doc_count=2)
        self.assertEqual(decision.intent, QueryIntent.WEB_SEARCH)
        self.assertEqual(decision.params.get("timeframe"), "w")
        self.assertEqual(decision.params.get("query").lower(), "news")

    def test_03_search_and_send_executes_pending_search(self):
        """3. 'Search and send me the answer' executes a pending search from history without another acknowledgement."""
        chat_hist = (
            "User: Give me latest news from recent week.\n"
            "Assistant: I'll perform a web search to fetch the latest news from this past week for you."
        )
        
        # Test direct command
        query = "Search and send me the answer"
        self.assertTrue(is_web_search_continuation(query, chat_history_str=chat_hist))
        
        decision = classify_query(query, doc_count=2, chat_history_str=chat_hist)
        self.assertEqual(decision.intent, QueryIntent.WEB_SEARCH)
        self.assertEqual(decision.sub_action, "web_search_followup")
        self.assertTrue(decision.params.get("is_continuation"))
        self.assertEqual(decision.params.get("timeframe"), "w")
        self.assertIn("news", decision.params.get("query").lower())

        # Test polite variant: "Yes please search and send me the answer"
        query_polite = "Yes please search and send me the answer."
        dec_polite = classify_query(query_polite, doc_count=2, chat_history_str=chat_hist)
        self.assertEqual(dec_polite.intent, QueryIntent.WEB_SEARCH)
        self.assertTrue(dec_polite.params.get("is_continuation"))

    def test_04_successful_search_returns_actual_mocked_results(self):
        """4. Successful search returns actual mocked headlines, summaries, sources, dates, and URLs."""
        mock_raw_output = (
            "snippet: AI labs unveiled major reasoning models this week with breakthrough performance., "
            "title: AI Breakthroughs Announced This Week, link: https://www.reuters.com/technology/ai-2026], ["
            "snippet: Renewable energy investments hit an all-time high over the past seven days., "
            "title: Global Green Energy Surge, link: https://apnews.com/article/green-energy-record]"
        )

        with patch("langchain_community.tools.DuckDuckGoSearchResults.invoke", return_value=mock_raw_output):
            search_data = search_web_structured("latest tech news", timeframe="w", max_results=2)
            
            self.assertEqual(search_data["status"], "success")
            self.assertEqual(len(search_data["results"]), 2)
            
            first = search_data["results"][0]
            self.assertEqual(first["title"], "AI Breakthroughs Announced This Week")
            self.assertEqual(first["source"], "reuters.com")
            self.assertEqual(first["url"], "https://www.reuters.com/technology/ai-2026")
            self.assertEqual(first["date"], "Last 7 days")
            self.assertIn("AI labs unveiled major reasoning models", first["snippet"])

            # Verify prompt context formatting
            ctx = format_web_search_context(search_data)
            self.assertIn("### Live Web Search Results for \"latest tech news\" (Last 7 days)", ctx)
            self.assertIn("reuters.com", ctx)
            self.assertIn("https://www.reuters.com/technology/ai-2026", ctx)

    def test_05_provider_failure_produces_honest_error(self):
        """5. Provider failure produces an honest error and never fabricates results or claims search succeeded."""
        # Test simulated timeout / exception
        with patch("backend.services.web_search_service.search_web_structured", side_effect=Exception("Connection reset")):
            async def run_failure():
                from backend.services.chat_service import stream_chat_events
                events = []
                u_thread = f"test_err_{uuid.uuid4().hex[:6]}"
                async for evt in stream_chat_events("Give me latest news from recent week.", "gemini-2.5-flash", u_thread):
                    events.append(evt)

                # Verify meta emitted 0 retrieved docs
                has_empty_docs = any('"source": "Web Search"' in e and '"retrieved_docs": []' in e for e in events)
                self.assertTrue(has_empty_docs, "Must emit empty retrieved_docs on provider failure")

                # Verify honest error token is streamed
                tokens = [e for e in events if '"type": "token"' in e or '"type":"token"' in e]
                combined = "".join(tokens)
                self.assertIn("returned no results or timed out", combined)
                self.assertNotIn("I'll perform a web search", combined)

            asyncio.run(run_failure())

    def test_06_general_knowledge_does_not_invoke_web_search(self):
        """6. General knowledge questions do NOT unnecessarily invoke web search."""
        gk_queries = [
            "Write a python quicksort implementation",
            "What is the difference between TCP and UDP?",
            "Explain quantum computing basics",
            "How do promises work in JavaScript?"
        ]
        for q in gk_queries:
            with self.subTest(query=q):
                self.assertFalse(is_explicit_web_search(q))
                decision = classify_query(q, doc_count=2)
                self.assertEqual(decision.intent, QueryIntent.GENERAL_KNOWLEDGE)
                self.assertFalse(decision.rag_invoked)
                self.assertNotIn("web_search", decision.tools_selected)


if __name__ == "__main__":
    unittest.main()

