"""
Comprehensive Test Suite for Web Image Search & Visual Retrieval Feature
Tests routing, query extraction, image retrieval providers, error resilience,
FastAPI endpoints, and SSE streaming separation from RAG.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import asyncio

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.router import classify_query, QueryIntent, RoutingDecision
from backend.tools import detect_image_search_intent
from backend.services.image_search_service import (
    search_web_images,
    search_web_images_async,
    clean_source_domain,
    _search_wikimedia_commons
)
from fastapi.testclient import TestClient
from server import app


class TestImageSearchRouting(unittest.TestCase):
    """Verifies that intent classification routes visual queries to IMAGE_SEARCH without hijacking RAG."""

    def test_image_search_intent_queries(self):
        test_cases = [
            ("show me pictures of the James Webb telescope", "the james webb telescope", False),
            ("find images of golden gate bridge", "golden gate bridge", False),
            ("diagram of human heart", "human heart", True),
            ("show diagrams of neural network architecture", "neural network architecture", True),
            ("image search for cute red panda", "cute red panda", False),
            ("pictures of quantum computer", "quantum computer", False),
            ("photos of saturn rings please", "saturn rings", False),
            ("visuals of photosynthesis process", "photosynthesis process", False),
            ("can you show me pictures of cats?", "cats", False),
            ("schematic of jet engine", "jet engine", True),
            ("transformer architecture diagram", "transformer architecture", True),
            ("search for pictures of aurora borealis", "aurora borealis", False),
        ]

        for query, expected_clean, expected_diag in test_cases:
            with self.subTest(query=query):
                decision = classify_query(query, doc_count=2)
                self.assertEqual(
                    decision.intent, 
                    QueryIntent.IMAGE_SEARCH,
                    f"Query '{query}' was not classified as IMAGE_SEARCH (got {decision.intent})"
                )
                self.assertFalse(decision.rag_invoked, "RAG was invoked for image search query")
                self.assertIn("image_search", decision.tools_selected)
                self.assertEqual(decision.selected_path, "web_image_search")
                self.assertEqual(decision.params.get("search_query"), expected_clean)
                self.assertEqual(decision.params.get("is_diagram"), expected_diag)

    def test_document_queries_not_hijacked(self):
        """Document queries referencing uploaded files/PDFs must NEVER route to IMAGE_SEARCH."""
        doc_queries = [
            "explain this diagram in my document",
            "show the diagram from my pdf",
            "explain the architecture diagram in the uploaded doc",
            "diagram of bellman ford according to my notes",
            "find the diagram in my coursework"
        ]

        for q in doc_queries:
            with self.subTest(query=q):
                decision = classify_query(q, doc_count=3)
                self.assertNotEqual(
                    decision.intent, 
                    QueryIntent.IMAGE_SEARCH,
                    f"Document query '{q}' was incorrectly hijacked by IMAGE_SEARCH!"
                )
                self.assertEqual(decision.intent, QueryIntent.DOCUMENT_RAG)
                self.assertTrue(decision.rag_invoked)

    def test_conversational_and_email_not_hijacked(self):
        """Conversational pleasantries and other tools must not be hijacked."""
        queries = [
            ("hello", QueryIntent.CONVERSATIONAL),
            ("how are you doing", QueryIntent.CONVERSATIONAL),
            ("check my emails from Sarah", QueryIntent.GMAIL),
            ("schedule a meeting with Bob", QueryIntent.CALENDAR),
            ("add a task to buy groceries", QueryIntent.TASK),
            ("search the web for latest AI news", QueryIntent.WEB_SEARCH),
        ]

        for q, expected_intent in queries:
            with self.subTest(query=q):
                decision = classify_query(q, doc_count=1)
                self.assertEqual(decision.intent, expected_intent)


class TestImageSearchService(unittest.TestCase):
    """Tests the image search provider execution, formatting, and fallbacks."""

    def test_clean_source_domain(self):
        self.assertEqual(clean_source_domain("https://www.nasa.gov/mission_pages"), "nasa.gov")
        self.assertEqual(clean_source_domain("https://en.wikipedia.org/wiki/Cat"), "en.wikipedia.org")
        self.assertEqual(clean_source_domain("http://pixabay.com/photo/123"), "pixabay.com")
        self.assertEqual(clean_source_domain("", default="Custom"), "Custom")

    def test_search_web_images_empty_query(self):
        res = search_web_images("")
        self.assertEqual(res["count"], 0)
        self.assertEqual(res["images"], [])

    def test_search_web_images_structure(self):
        """Tests that retrieved image records strictly follow the expected schema."""
        res = search_web_images("Apollo 11 lunar module", max_results=3)
        self.assertIn("images", res)
        self.assertIn("provider", res)
        self.assertGreater(len(res["images"]), 0)

        first = res["images"][0]
        self.assertIn("title", first)
        self.assertIn("image", first)
        self.assertIn("thumbnail", first)
        self.assertIn("url", first)
        self.assertIn("source", first)
        self.assertTrue(first["image"].startswith("http"))
        self.assertTrue(first["thumbnail"].startswith("http"))

    def test_fallback_to_wikimedia_when_primary_fails(self):
        """When DDGS raises an exception or returns empty, Wikimedia Commons handles the request."""
        with patch("backend.services.image_search_service._search_ddgs", return_value=[]):
            res = search_web_images("mitochondria", max_results=2, prefer_diagrams=True)
            self.assertEqual(res["provider"], "Wikimedia Commons")
            self.assertGreater(len(res["images"]), 0)
            self.assertIn("commons.wikimedia.org", res["images"][0]["source"])

    def test_async_wrapper_timeout_resilience(self):
        """Ensures that async image search handles simulated timeouts gracefully."""
        async def run_timeout_test():
            with patch("backend.services.image_search_service.search_web_images", side_effect=asyncio.TimeoutError):
                res = await search_web_images_async("mars rover", max_results=2, timeout=0.01)
                self.assertEqual(res["images"], [])
        asyncio.run(run_timeout_test())


class TestImageSearchAPIEndpoint(unittest.TestCase):
    """Tests the FastAPI REST endpoint for image search."""

    def setUp(self):
        self.client = TestClient(app)

    def test_endpoint_success(self):
        response = self.client.get("/api/images/search?q=hubble+space+telescope&limit=3")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("images", data)
        self.assertIn("provider", data)
        self.assertIsInstance(data["images"], list)

    def test_endpoint_validation_empty_query(self):
        response = self.client.get("/api/images/search?q=")
        self.assertEqual(response.status_code, 422)


class TestImageSearchStreamingEvents(unittest.TestCase):
    """Tests that stream_chat_events yields proper SSE events for image search."""

    def test_stream_image_events(self):
        async def run_stream():
            from backend.services.chat_service import stream_chat_events
            events = []
            async for evt in stream_chat_events("show me pictures of jupiter", "gemini-2.5-flash", "test_img_thread"):
                events.append(evt)

            # Check that stage event was emitted
            has_stage = any('"stage":"searching_images"' in e for e in events)
            self.assertTrue(has_stage, "Did not emit searching_images stage event")

            # Check that meta event with images was emitted
            has_images_meta = any('"source": "Image Search"' in e and '"images":' in e for e in events)
            self.assertTrue(has_images_meta, "Did not emit meta event with Image Search source and images")

            # Check that dedicated images event was emitted
            has_images_type = any('"type": "images"' in e for e in events)
            self.assertTrue(has_images_type, "Did not emit dedicated images SSE event")

            # Check that introductory token was streamed
            has_token = any('"type": "token"' in e for e in events)
            self.assertTrue(has_token, "Did not stream introductory token")

        asyncio.run(run_stream())




class TestImageSearchContextResolution(unittest.TestCase):
    """
    Offline regression tests for context-aware entity resolution in Web Image Search.
    Verifies that pronouns ('his', 'her', 'its', 'their', 'them') are deterministically
    resolved to previous entities from general knowledge or conversation history,
    without making ANY external AI or Gemini API calls.
    """

    def test_case_1_sam_altman_his_img(self):
        """User asks 'Who is Sam Altman?' followed by 'Can you show his img?' -> resolves to 'Sam Altman'."""
        chat_hist = "User: Who is Sam Altman?\nAssistant: Sam Altman is an American entrepreneur and the CEO of OpenAI."
        query = "Can you show his img?"
        decision = classify_query(query, doc_count=2, chat_history_str=chat_hist)
        
        self.assertEqual(decision.intent, QueryIntent.IMAGE_SEARCH)
        self.assertFalse(decision.rag_invoked)
        self.assertEqual(decision.params.get("search_query"), "Sam Altman")
        self.assertFalse(decision.params.get("needs_clarification", False))

    def test_case_2_elon_musk_his_photo(self):
        """User asks 'Who is Elon Musk?' followed by 'show his photo' -> resolves to 'Elon Musk'."""
        chat_hist = "User: Who is Elon Musk?\nAssistant: Elon Musk is the CEO of Tesla and SpaceX."
        query = "show his photo"
        decision = classify_query(query, doc_count=2, chat_history_str=chat_hist)
        
        self.assertEqual(decision.intent, QueryIntent.IMAGE_SEARCH)
        self.assertFalse(decision.rag_invoked)
        self.assertEqual(decision.params.get("search_query"), "Elon Musk")
        self.assertFalse(decision.params.get("needs_clarification", False))

    def test_case_3_company_its_logo(self):
        """User asks 'Tell me about Anthropic.' followed by 'show its logo' -> resolves to 'Anthropic logo'."""
        chat_hist = "User: Tell me about Anthropic.\nAssistant: Anthropic is an AI safety startup founded in 2021 that develops Claude."
        query = "show its logo"
        decision = classify_query(query, doc_count=2, chat_history_str=chat_hist)
        
        self.assertEqual(decision.intent, QueryIntent.IMAGE_SEARCH)
        self.assertFalse(decision.rag_invoked)
        self.assertEqual(decision.params.get("search_query"), "Anthropic logo")
        self.assertFalse(decision.params.get("needs_clarification", False))

    def test_case_4_multi_entity_disambiguation(self):
        """
        When history contains multiple entities ('Elon Musk' and 'Marie Curie'),
        'Show his image' must resolve to Elon Musk, and 'Show her image' must resolve to Marie Curie.
        """
        chat_hist = (
            "User: Compare Elon Musk and Marie Curie.\n"
            "Assistant: Elon Musk is a modern technology entrepreneur leading Tesla. "
            "Marie Curie was a pioneering physicist and chemist who discovered radium."
        )
        # Test male pronoun resolution
        dec_male = classify_query("Show his image", doc_count=2, chat_history_str=chat_hist)
        self.assertEqual(dec_male.intent, QueryIntent.IMAGE_SEARCH)
        self.assertEqual(dec_male.params.get("search_query"), "Elon Musk")

        # Test female pronoun resolution
        dec_female = classify_query("Show her image", doc_count=2, chat_history_str=chat_hist)
        self.assertEqual(dec_female.intent, QueryIntent.IMAGE_SEARCH)
        self.assertEqual(dec_female.params.get("search_query"), "Marie Curie")

    def test_case_5_no_previous_entity_clarification(self):
        """
        When there is no previous entity in history, 'Can you show his img?' must NOT
        execute a search on 'can you show his'. It must mark needs_clarification=True.
        """
        query = "Can you show his img?"
        decision = classify_query(query, doc_count=2, chat_history_str="")
        
        self.assertEqual(decision.intent, QueryIntent.IMAGE_SEARCH)
        self.assertTrue(decision.params.get("needs_clarification"))
        self.assertIsNone(decision.params.get("search_query"))

    def test_forbidden_search_terms_never_searched(self):
        """Imperative prefixes and pronoun fragments must NEVER be treated as valid search subjects."""
        from backend.tools import FORBIDDEN_SEARCH_TERMS
        forbidden_test_samples = [
            "can you show his", "show his", "show me his", "show her",
            "show its", "show their", "his img", "her img", "show", "image"
        ]
        for term in forbidden_test_samples:
            self.assertIn(term, FORBIDDEN_SEARCH_TERMS)

    def test_clarification_streaming_zero_external_calls(self):
        """Verifies that an ambiguous pronoun query with empty history yields clarification with 0 external calls."""
        async def run_clarification():
            from backend.services.chat_service import stream_chat_events
            with patch("backend.services.image_search_service.search_web_images_async") as mock_img_search:
                events = []
                import uuid
                unique_thread = f"test_thread_empty_{uuid.uuid4().hex[:8]}"
                async for evt in stream_chat_events("Can you show his img?", "gemini-2.5-flash", unique_thread):
                    events.append(evt)
                
                # Verify external image search was NEVER invoked
                mock_img_search.assert_not_called()

                # Verify clarification token was streamed
                tokens = [evt for evt in events if '"type": "token"' in evt or '"type":"token"' in evt]
                combined_tokens = "".join(tokens)
                self.assertIn("clarify who or what", combined_tokens)

        asyncio.run(run_clarification())


if __name__ == "__main__":
    unittest.main()

