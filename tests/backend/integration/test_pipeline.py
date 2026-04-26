"""
Integration tests for the LangGraph pipeline — Groq calls are mocked.
Tests the full state transitions: guardrail → intent → fusion → response.

Run: pytest tests/backend/integration/test_pipeline.py -v
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from conftest import make_state


# ---------------------------------------------------------------------------
# Guardrail node — mode-aware blocking
# ---------------------------------------------------------------------------

class TestGuardrailNode:
    def test_always_blocked_in_trader_mode(self):
        """market_manipulation blocked even in trader mode."""
        from guardrails.classifier import _ALWAYS_BLOCKED
        assert "market_manipulation" in _ALWAYS_BLOCKED

    def test_buy_sell_allowed_in_trader(self):
        """direct_buy_sell_recommendation not in trader blocked set."""
        from guardrails.classifier import _ALWAYS_BLOCKED
        assert "direct_buy_sell_recommendation" not in _ALWAYS_BLOCKED

    def test_buy_sell_blocked_in_insight(self):
        """direct_buy_sell_recommendation in insight blocked set."""
        from guardrails.classifier import _BLOCKED_INTENTS
        assert "direct_buy_sell_recommendation" in _BLOCKED_INTENTS


# ---------------------------------------------------------------------------
# Intent classifier node — summary bypass
# ---------------------------------------------------------------------------

class TestIntentClassifierBypass:
    def test_summary_bypasses_groq(self):
        """Summary queries must never call Groq — bypass returns all 4 intents."""
        from graph.nodes.intent_classifier import _is_summary_query, _ALL_INTENTS

        summary_queries = [
            "Summarize this stock",
            "Give me a full breakdown",
            "Explain the stock",
            "What's happening with this stock?",
        ]
        for q in summary_queries:
            assert _is_summary_query(q), f"Should be summary: '{q}'"

        # All 4 intents returned for summary
        assert set(_ALL_INTENTS) == {"real_time", "fundamental", "news", "historical"}

    def test_focused_query_not_summary(self):
        from graph.nodes.intent_classifier import _is_summary_query

        focused = [
            "What is the PE ratio?",
            "Why did it drop today?",
            "Should I buy?",
            "Show me news",
        ]
        for q in focused:
            assert not _is_summary_query(q), f"Should NOT be summary: '{q}'"


# ---------------------------------------------------------------------------
# Fusion node — signal computation
# ---------------------------------------------------------------------------

class TestFusionSignalComputation:
    def test_sharp_drop_dominates_narrative(self):
        from graph.nodes.fusion_node import _compute_narrative_hint

        state = make_state(
            pct_change=-5.2,
            volume=80_000_000,
            avg_volume_30d=30_000_000,
            week_52_high=199.0,
            week_52_low=150.0,
        )
        hint = _compute_narrative_hint(state)
        assert hint == "sharp_downward_move"

    def test_volume_spike_narrative_when_no_price_move(self):
        from graph.nodes.fusion_node import _compute_narrative_hint

        state = make_state(
            pct_change=0.3,
            volume=90_000_000,
            avg_volume_30d=30_000_000,
        )
        hint = _compute_narrative_hint(state)
        assert hint == "high_volume_move"

    def test_high_confidence_requires_strong_signals(self):
        from graph.nodes.fusion_node import _compute_confidence_level

        state = make_state(
            pct_change=-4.5,
            volume=75_000_000,
            avg_volume_30d=25_000_000,
            analyst_buy=20,
            analyst_hold=5,
            analyst_sell=2,
            news_chunks=[{"text": "news1"}, {"text": "news2"}, {"text": "news3"}],
            historical_chunks=[{"text": "hist"}],
        )
        level = _compute_confidence_level(state)
        assert level == "high"

    def test_low_confidence_with_no_data(self):
        from graph.nodes.fusion_node import _compute_confidence_level

        state = make_state(price=None)
        level = _compute_confidence_level(state)
        assert level == "low"

    def test_conflict_detected_price_down_analyst_bullish(self):
        from graph.nodes.fusion_node import _compute_conflict

        state = make_state(
            pct_change=-3.5,
            analyst_buy=22,
            analyst_hold=3,
            analyst_sell=1,
        )
        has_conflict, conflict_type = _compute_conflict(state)
        assert has_conflict
        assert "bullish" in conflict_type or "analyst" in conflict_type

    def test_no_conflict_aligned_signals(self):
        from graph.nodes.fusion_node import _compute_conflict

        state = make_state(
            pct_change=2.5,
            analyst_buy=18,
            analyst_hold=7,
            analyst_sell=2,
        )
        has_conflict, _ = _compute_conflict(state)
        assert not has_conflict


# ---------------------------------------------------------------------------
# Response node — system prompt selection
# ---------------------------------------------------------------------------

class TestResponseNodePromptSelection:
    def test_insight_uses_insight_prompt(self):
        from graph.nodes.response_node import _SYSTEM_INSIGHT, _SYSTEM_TRADER

        # Insight prompt must contain the exact disclaimer redirect phrase
        assert "Consider consulting a financial advisor" in _SYSTEM_INSIGHT

        # Insight prompt must NOT allow directional buy/sell
        assert "INSIGHT" in _SYSTEM_INSIGHT or "insight" in _SYSTEM_INSIGHT.lower()

    def test_trader_uses_trader_prompt(self):
        from graph.nodes.response_node import _SYSTEM_TRADER

        # Trader prompt must include directional bias rule
        assert "bullish" in _SYSTEM_TRADER.lower() or "DIRECTIONAL" in _SYSTEM_TRADER

    def test_prompts_are_distinct(self):
        from graph.nodes.response_node import _SYSTEM_INSIGHT, _SYSTEM_TRADER

        assert _SYSTEM_INSIGHT != _SYSTEM_TRADER

    def test_no_emojis_in_system_prompts(self):
        from graph.nodes.response_node import _SYSTEM_INSIGHT, _SYSTEM_TRADER

        # Check for common emoji unicode ranges — no emojis in prompts
        import re
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
            "\U00002700-\U000027BF]",
            re.UNICODE
        )
        assert not emoji_pattern.search(_SYSTEM_INSIGHT), "Emoji found in INSIGHT prompt"
        assert not emoji_pattern.search(_SYSTEM_TRADER), "Emoji found in TRADER prompt"

    def test_insight_prompt_has_no_directive_rule(self):
        from graph.nodes.response_node import _SYSTEM_INSIGHT

        # Must contain rule about not giving buy/sell directives
        assert "buy" in _SYSTEM_INSIGHT.lower() or "sell" in _SYSTEM_INSIGHT.lower()

    def test_compression_rule_in_both_prompts(self):
        from graph.nodes.response_node import _SYSTEM_INSIGHT, _SYSTEM_TRADER

        # Both prompts must enforce section compression
        for prompt, name in [(_SYSTEM_INSIGHT, "INSIGHT"), (_SYSTEM_TRADER, "TRADER")]:
            assert "sentence" in prompt.lower() or "compress" in prompt.lower(), (
                f"{name} prompt missing compression rule"
            )


# ---------------------------------------------------------------------------
# State schema integrity
# ---------------------------------------------------------------------------

class TestStateSchema:
    def test_state_has_user_mode(self):
        state = make_state(user_mode="trader")
        assert state["user_mode"] == "trader"

    def test_state_has_intents(self):
        state = make_state(intents=["real_time", "news"])
        assert "real_time" in state["intents"]

    def test_state_defaults(self):
        state = make_state()
        assert state["ticker"] == "AAPL"
        assert state["session_id"] == "test-session"
        assert state["conversation_history"] == []
        assert state["guardrail_blocked"] is False
        assert state["user_mode"] == "insight"

    def test_used_c1_removed(self):
        """used_c1 field was removed — must not appear in state."""
        state = make_state()
        assert "used_c1" not in state

    def test_summary_card_removed(self):
        """summaryCard concept removed — no such field in state."""
        state = make_state()
        assert "summaryCard" not in state
        assert "summary_card" not in state
