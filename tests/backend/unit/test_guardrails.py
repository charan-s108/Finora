"""
Unit tests for guardrail mode logic — no API calls.
Tests the blocked intent sets and trader vs insight separation.

Run: pytest tests/backend/unit/test_guardrails.py -v
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../backend"))

from guardrails.classifier import _ALWAYS_BLOCKED, _INSIGHT_ONLY_BLOCKED, _BLOCKED_INTENTS


class TestGuardrailSets:
    def test_always_blocked_contains_critical_intents(self):
        assert "insider_trading_context" in _ALWAYS_BLOCKED
        assert "market_manipulation" in _ALWAYS_BLOCKED
        assert "tax_evasion_advice" in _ALWAYS_BLOCKED
        assert "specific_options_strategy" in _ALWAYS_BLOCKED

    def test_buy_sell_not_always_blocked(self):
        # Trader mode should allow buy/sell through
        assert "direct_buy_sell_recommendation" not in _ALWAYS_BLOCKED

    def test_buy_sell_insight_only_blocked(self):
        assert "direct_buy_sell_recommendation" in _INSIGHT_ONLY_BLOCKED

    def test_personal_planning_insight_only_blocked(self):
        assert "personal_financial_planning" in _INSIGHT_ONLY_BLOCKED

    def test_full_blocked_set_is_union(self):
        assert _BLOCKED_INTENTS == _ALWAYS_BLOCKED | _INSIGHT_ONLY_BLOCKED

    def test_trader_mode_blocked_set_excludes_buy_sell(self):
        trader_blocked = _ALWAYS_BLOCKED
        assert "direct_buy_sell_recommendation" not in trader_blocked
        assert "personal_financial_planning" not in trader_blocked

    def test_insight_mode_blocked_set_includes_buy_sell(self):
        assert "direct_buy_sell_recommendation" in _BLOCKED_INTENTS

    def test_no_overlap_always_and_insight_only(self):
        # Sets should not overlap (each intent in exactly one)
        overlap = _ALWAYS_BLOCKED & _INSIGHT_ONLY_BLOCKED
        assert len(overlap) == 0


class TestGuardrailModeRouting:
    def test_trader_uses_always_blocked_only(self):
        user_mode = "trader"
        blocked_set = _ALWAYS_BLOCKED if user_mode == "trader" else _BLOCKED_INTENTS
        assert blocked_set == _ALWAYS_BLOCKED

    def test_insight_uses_full_blocked_set(self):
        user_mode = "insight"
        blocked_set = _ALWAYS_BLOCKED if user_mode == "trader" else _BLOCKED_INTENTS
        assert blocked_set == _BLOCKED_INTENTS

    @pytest.mark.parametrize("intent", [
        "insider_trading_context",
        "market_manipulation",
        "tax_evasion_advice",
        "specific_options_strategy",
    ])
    def test_always_blocked_in_both_modes(self, intent):
        assert intent in _ALWAYS_BLOCKED
        assert intent in _BLOCKED_INTENTS

    @pytest.mark.parametrize("intent", [
        "direct_buy_sell_recommendation",
        "personal_financial_planning",
    ])
    def test_conditionally_blocked_only_in_insight(self, intent):
        assert intent not in _ALWAYS_BLOCKED
        assert intent in _BLOCKED_INTENTS
