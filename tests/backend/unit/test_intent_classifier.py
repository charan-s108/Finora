"""
Unit tests for intent_classifier_node — summary bypass (no API call).

Run: pytest tests/backend/unit/test_intent_classifier.py -v
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from graph.nodes.intent_classifier import _is_summary_query, _ALL_INTENTS
from conftest import make_state


class TestSummaryBypass:
    """Summary queries must bypass LLM and return all 4 intents deterministically."""

    def test_summarize_returns_all_intents(self):
        assert _is_summary_query("Summarize this stock")

    def test_summary_keyword_triggers(self):
        triggers = [
            "Summarize AAPL",
            "Give me a summary",
            "Explain this stock",
            "Overview of the company",
            "What's happening with this stock?",
            "Tell me about MSFT",
            "Give me a breakdown",
            "Analyse Apple",
            "Analyze the stock",
            "What do you think about this?",
            "How is this stock doing?",
            "How's AAPL performing?",
        ]
        for q in triggers:
            assert _is_summary_query(q), f"Expected summary trigger: '{q}'"

    def test_focused_queries_not_summary(self):
        non_triggers = [
            "What is the current price?",
            "What is the PE ratio?",
            "Why did Apple drop today?",
            "Show me recent news",
            "What are analysts saying?",
            "Is this stock bullish?",
            "Should I buy?",
            "What is EPS?",
            "Compare AAPL and MSFT",
            "",
        ]
        for q in non_triggers:
            assert not _is_summary_query(q), f"Expected NOT a summary trigger: '{q}'"

    def test_all_intents_constant(self):
        assert set(_ALL_INTENTS) == {"real_time", "fundamental", "news", "historical"}
        assert len(_ALL_INTENTS) == 4

    def test_summary_fires_all_4_branches(self):
        # Simulate what intent_classifier_node does for summary queries
        # Without calling Groq — verify the bypass logic
        query = "Summarize this stock"
        if _is_summary_query(query):
            intents = _ALL_INTENTS
        else:
            intents = ["real_time", "news"]  # default fallback
        assert set(intents) == {"real_time", "fundamental", "news", "historical"}
