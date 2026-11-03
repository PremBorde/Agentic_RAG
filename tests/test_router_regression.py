"""
Permanent Regression Test Suite for Centralized QueryIntent Router
Ensures that substantive requests are NEVER hijacked by conversational fast paths,
while genuine greetings and pleasantries retain their zero-LLM fast path.
"""

import unittest
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.router import classify_query, QueryIntent, RoutingDecision

class RouterRegressionTests(unittest.TestCase):

    # ── CATEGORY 1: FALSE-POSITIVE REGRESSION TESTS ──────────────────────────
    def test_false_positives_not_conversational(self):
        """
        Critical regression test: Substantive requests starting with or containing
        conversational words (Now, Hi, Hey, No, Thanks, Notice, Normal, Hinglish, etc.)
        must NEVER be classified as QueryIntent.CONVERSATIONAL or fast-path.
        """
        false_positive_queries = [
            "Now prepare me for my practicals",
            "Explain this in Hinglish",
            "Notice the important points in my PDF",
            "Normal forms in DBMS",
            "I need help with my exam",
            "No, explain the previous answer",
            "Hi, search my uploaded PDF",
            "Hey, find the email from Rahul",
            "Thanks, now summarize the document",
            "Explain Dijkstra",
            "Search my PDF",
            "Find Sarah's email",
            "Book a meeting",
            "Now prepare me for the practicals as there is ny pratical tommoew so i need proper understanding of each of In short but precise in hinglish from the document"
        ]

        for q in false_positive_queries:
            with self.subTest(query=q):
                decision = classify_query(q, doc_count=1)
                self.assertNotEqual(
                    decision.intent, 
                    QueryIntent.CONVERSATIONAL,
                    f"FAILED: Query '{q}' was hijacked as CONVERSATIONAL! Reason: {decision.reason}"
                )
                self.assertFalse(
                    decision.is_fast_path,
                    f"FAILED: Query '{q}' was marked as fast-path!"
                )
                self.assertFalse(
                    decision.is_welcome_card,
                    f"FAILED: Query '{q}' triggered welcome card!"
                )

    # ── CATEGORY 2: GENUINE CONVERSATIONAL TESTS ────────────────────────────
    def test_genuine_conversational_queries(self):
        """
        Genuine greetings and pleasantries must retain zero-LLM fast-path behavior.
        """
        genuine_greetings = [
            ("Hi", True),
            ("Hello", True),
            ("Hey", True),
            ("Heyyyyyyy", True),
            ("Good morning", True),
            ("Good afternoon", True),
            ("Good evening", True),
            ("What can you do?", True),
            ("Who are you?", True),
            ("Thanks", False),
            ("Thank you", False),
            ("No", False),
            ("Nope", False),
            ("I'm good", False),
            ("Ok", False),
            ("Cool", False),
            ("Got it", False),
        ]

        for q, expected_welcome in genuine_greetings:
            with self.subTest(query=q):
                decision = classify_query(q, doc_count=1)
                self.assertEqual(
                    decision.intent, 
                    QueryIntent.CONVERSATIONAL,
                    f"FAILED: Genuine small talk '{q}' was NOT classified as CONVERSATIONAL! Got {decision.intent}"
                )
                self.assertTrue(
                    decision.is_fast_path,
                    f"FAILED: Query '{q}' was not marked as fast-path!"
                )
                self.assertEqual(
                    decision.is_welcome_card, 
                    expected_welcome,
                    f"FAILED: Query '{q}' welcome card expectation mismatch (got {decision.is_welcome_card}, expected {expected_welcome})"
                )

    # ── CATEGORY 3: MULTI-INTENT TESTS ──────────────────────────────────────
    def test_multi_intent_routing(self):
        """
        Compound multi-step queries must reach agent orchestration.
        """
        multi_queries = [
            ("Find Rahul's email and schedule a meeting for tomorrow", "email_and_calendar"),
            ("Search my email for feedback and schedule a meeting", "email_and_calendar"),
            ("Find the email from client and add a task to review it", "email_and_task"),
            ("Check inbox for project updates and create a task", "email_and_task"),
        ]

        for q, expected_sub in multi_queries:
            with self.subTest(query=q):
                decision = classify_query(q, doc_count=1)
                self.assertEqual(
                    decision.intent,
                    QueryIntent.MULTI_STEP,
                    f"FAILED: Multi-intent query '{q}' did not route to MULTI_STEP! Got {decision.intent}"
                )
                self.assertEqual(
                    decision.sub_action,
                    expected_sub,
                    f"FAILED: Multi-intent sub_action mismatch for '{q}'! Got {decision.sub_action}"
                )
                self.assertFalse(decision.is_fast_path)

    # ── CATEGORY 4: FOLLOW-UP CONTEXT TESTS ─────────────────────────────────
    def test_followup_context_routing(self):
        """
        Follow-up queries with active history must retain context and route to RAG / LLM.
        """
        followups = [
            "Explain the next one.",
            "Continue.",
            "What about its complexity?",
            "Now explain it in Hinglish.",
            "Tell me more about points 2 and 3."
        ]

        for q in followups:
            with self.subTest(query=q):
                decision = classify_query(q, doc_count=1, has_history=True)
                self.assertNotEqual(
                    decision.intent,
                    QueryIntent.CONVERSATIONAL,
                    f"FAILED: Follow-up query '{q}' was hijacked as CONVERSATIONAL!"
                )
                self.assertFalse(decision.is_fast_path)
                self.assertFalse(decision.is_welcome_card)
                self.assertTrue(
                    decision.intent in (QueryIntent.DOCUMENT_RAG, QueryIntent.GENERAL_KNOWLEDGE),
                    f"FAILED: Follow-up '{q}' routed to unexpected intent: {decision.intent}"
                )

    # ── CATEGORY 5: SHORT SUBSTANTIVE QUERIES (RULE C) ──────────────────────
    def test_short_substantive_queries(self):
        """
        Rule C: Length is NOT an intent signal. Short queries with substantive verbs
        or objects must never be hijacked.
        """
        short_queries = [
            "Explain Dijkstra.",
            "Search my PDF.",
            "Find Sarah's email.",
            "Book a meeting.",
            "Create a task.",
            "What is KNN?",
        ]

        for q in short_queries:
            with self.subTest(query=q):
                decision = classify_query(q, doc_count=1)
                self.assertNotEqual(
                    decision.intent,
                    QueryIntent.CONVERSATIONAL,
                    f"FAILED: Short substantive query '{q}' was hijacked as CONVERSATIONAL!"
                )

if __name__ == "__main__":
    unittest.main()

