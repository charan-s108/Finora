"""
Unit tests for fusion_node signal computation.
All functions are pure/deterministic — no API calls, no mocking needed.

Run: pytest tests/backend/unit/test_fusion_signals.py -v
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../backend"))

from graph.nodes.fusion_node import (
    _is_summary_query,
    _compute_narrative_hint,
    _compute_confidence_level,
    _compute_conflict,
    _compute_insight_flags,
    _compute_price_trend,
    _build_data_context,
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from conftest import make_state


# ---------------------------------------------------------------------------
# _is_summary_query
# ---------------------------------------------------------------------------

class TestIsSummaryQuery:
    def test_summarize_trigger(self):
        assert _is_summary_query("Summarize this stock") is True

    def test_summary_trigger(self):
        assert _is_summary_query("Give me a summary of AAPL") is True

    def test_explain_trigger(self):
        assert _is_summary_query("Explain this stock to me") is True

    def test_overview_trigger(self):
        assert _is_summary_query("overview of RELIANCE") is True

    def test_whats_happening_trigger(self):
        assert _is_summary_query("What's happening with this stock?") is True

    def test_analyse_trigger(self):
        assert _is_summary_query("Analyse Apple Inc") is True

    def test_focused_price_query_not_summary(self):
        assert _is_summary_query("What is the current price?") is False

    def test_focused_pe_query_not_summary(self):
        assert _is_summary_query("What is the PE ratio?") is False

    def test_focused_news_query_not_summary(self):
        assert _is_summary_query("Why did AAPL drop today?") is False

    def test_empty_query_not_summary(self):
        assert _is_summary_query("") is False


# ---------------------------------------------------------------------------
# _compute_narrative_hint
# ---------------------------------------------------------------------------

class TestNarrativeHint:
    def test_sharp_drop_dominates(self):
        state = make_state(pct_change=-5.0, volume=30_000_000, avg_volume_30d=25_000_000)
        assert _compute_narrative_hint(state) == "sharp_downward_move"

    def test_sharp_rise_dominates(self):
        state = make_state(pct_change=4.2)
        assert _compute_narrative_hint(state) == "sharp_upward_move"

    def test_volume_spike_beats_moderate_move(self):
        state = make_state(pct_change=1.5, volume=70_000_000, avg_volume_30d=25_000_000)
        assert _compute_narrative_hint(state) == "high_volume_move"

    def test_near_52w_high(self):
        # price = 199, range 150-200 → pos = 98%
        state = make_state(pct_change=0.5, price=199.0, week_52_high=200.0, week_52_low=150.0,
                           volume=25_000_000, avg_volume_30d=25_000_000)
        assert _compute_narrative_hint(state) == "near_52w_high"

    def test_near_52w_low(self):
        # price = 152, range 150-200 → pos = 4%
        state = make_state(pct_change=-0.5, price=152.0, week_52_high=200.0, week_52_low=150.0,
                           volume=25_000_000, avg_volume_30d=25_000_000)
        assert _compute_narrative_hint(state) == "near_52w_low"

    def test_strong_analyst_bullish(self):
        state = make_state(pct_change=0.3, analyst_buy=30, analyst_hold=4, analyst_sell=0)
        assert _compute_narrative_hint(state) == "analyst_strongly_bullish"

    def test_analyst_bearish(self):
        state = make_state(pct_change=0.1, analyst_buy=3, analyst_hold=8, analyst_sell=10)
        assert _compute_narrative_hint(state) == "analyst_bearish"

    def test_mild_upward(self):
        state = make_state(pct_change=1.5, analyst_buy=10, analyst_hold=10, analyst_sell=5)
        assert _compute_narrative_hint(state) == "mild_upward_move"

    def test_mild_downward(self):
        state = make_state(pct_change=-1.5, analyst_buy=10, analyst_hold=10, analyst_sell=5)
        assert _compute_narrative_hint(state) == "mild_downward_move"

    def test_consolidating_default(self):
        state = make_state(pct_change=0.2, analyst_buy=10, analyst_hold=10, analyst_sell=5)
        assert _compute_narrative_hint(state) == "consolidating"

    def test_no_realtime_data(self):
        state = make_state(price=None)
        # No realtime → should not crash, returns consolidating or analyst signal
        result = _compute_narrative_hint(state)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _compute_confidence_level
# ---------------------------------------------------------------------------

class TestConfidenceLevel:
    def test_high_confidence_multiple_strong_signals(self):
        # Large move + volume spike + near 52W extreme + news
        state = make_state(
            pct_change=-4.5,
            volume=80_000_000,
            avg_volume_30d=25_000_000,
            price=151.0,
            week_52_high=200.0,
            week_52_low=150.0,
            news_chunks=[{"text": "breaking news", "url": "http://x.com"}],
            historical_chunks=[{"text": "historical pattern"}],
        )
        assert _compute_confidence_level(state) == "high"

    def test_medium_confidence_one_strong_signal(self):
        state = make_state(
            pct_change=2.5,  # strong move
            volume=26_000_000,  # normal volume
            news_chunks=[{"text": "news item"}],
        )
        assert _compute_confidence_level(state) == "medium"

    def test_low_confidence_no_data(self):
        state = make_state(
            pct_change=0.3,
            volume=24_000_000,
            avg_volume_30d=25_000_000,
            news_chunks=[],
            historical_chunks=[],
        )
        assert _compute_confidence_level(state) == "low"

    def test_low_confidence_no_realtime(self):
        state = make_state(price=None, news_chunks=[], historical_chunks=[])
        assert _compute_confidence_level(state) == "low"

    def test_high_confidence_with_strong_analyst_consensus(self):
        state = make_state(
            pct_change=3.1,
            volume=60_000_000,
            avg_volume_30d=25_000_000,
            analyst_buy=28,
            analyst_hold=2,
            analyst_sell=0,
            news_chunks=[{"text": "news"}],
            historical_chunks=[{"text": "hist"}],
        )
        assert _compute_confidence_level(state) == "high"


# ---------------------------------------------------------------------------
# _compute_conflict
# ---------------------------------------------------------------------------

class TestConflictDetection:
    def test_price_down_analyst_bullish(self):
        state = make_state(pct_change=-3.5, analyst_buy=25, analyst_hold=5, analyst_sell=0)
        has_conflict, reason = _compute_conflict(state)
        assert has_conflict is True
        assert reason == "price_down_but_analyst_bullish"

    def test_price_up_analyst_cautious(self):
        state = make_state(pct_change=2.5, analyst_buy=5, analyst_hold=15, analyst_sell=10)
        has_conflict, reason = _compute_conflict(state)
        assert has_conflict is True
        assert reason == "price_up_but_analyst_cautious"

    def test_near_52w_low_analyst_bullish(self):
        # price near low, analysts bullish
        state = make_state(
            pct_change=-0.5,
            price=152.0,
            week_52_high=200.0,
            week_52_low=150.0,
            analyst_buy=22,
            analyst_hold=3,
            analyst_sell=0,
        )
        has_conflict, reason = _compute_conflict(state)
        assert has_conflict is True
        assert reason == "near_52w_low_but_analyst_bullish"

    def test_near_52w_high_target_below_price(self):
        # price 198, target 180 → analyst target below current
        state = make_state(
            price=198.0,
            week_52_high=200.0,
            week_52_low=150.0,
            analyst_target=175.0,
            pct_change=0.5,
        )
        has_conflict, reason = _compute_conflict(state)
        assert has_conflict is True
        assert reason == "near_52w_high_but_target_below_price"

    def test_no_conflict_aligned_signals(self):
        # price down, analysts also bearish → no conflict
        state = make_state(pct_change=-2.5, analyst_buy=4, analyst_hold=6, analyst_sell=15)
        has_conflict, reason = _compute_conflict(state)
        assert has_conflict is False
        assert reason == ""

    def test_no_conflict_price_up_analysts_bullish(self):
        state = make_state(pct_change=3.0, analyst_buy=25, analyst_hold=5, analyst_sell=0)
        has_conflict, _ = _compute_conflict(state)
        assert has_conflict is False


# ---------------------------------------------------------------------------
# _compute_insight_flags
# ---------------------------------------------------------------------------

class TestInsightFlags:
    def test_volume_spike_flagged(self):
        state = make_state(volume=70_000_000, avg_volume_30d=25_000_000)
        flags = _compute_insight_flags(state)
        assert any("Volume spike" in f for f in flags)

    def test_low_volume_flagged(self):
        state = make_state(volume=8_000_000, avg_volume_30d=25_000_000)
        flags = _compute_insight_flags(state)
        assert any("below average" in f for f in flags)

    def test_high_pe_flagged(self):
        state = make_state(pe=55.0)
        flags = _compute_insight_flags(state)
        assert any("premium valuation" in f for f in flags)

    def test_low_pe_flagged(self):
        state = make_state(pe=8.0)
        flags = _compute_insight_flags(state)
        assert any("below typical market average" in f for f in flags)

    def test_forward_pe_growth_signal(self):
        # fpe much lower than pe → earnings growth expected
        state = make_state(pe=30.0, forward_pe=20.0)
        flags = _compute_insight_flags(state)
        assert any("earnings growth expected" in f for f in flags)

    def test_near_52w_high_flagged(self):
        state = make_state(price=199.0, week_52_high=200.0, week_52_low=150.0)
        flags = _compute_insight_flags(state)
        assert any("52-week high" in f for f in flags)

    def test_near_52w_low_flagged(self):
        state = make_state(price=151.5, week_52_high=200.0, week_52_low=150.0)
        flags = _compute_insight_flags(state)
        assert any("52-week low" in f for f in flags)

    def test_strong_buy_consensus_flagged(self):
        state = make_state(analyst_buy=30, analyst_hold=2, analyst_sell=0)
        flags = _compute_insight_flags(state)
        assert any("Strong buy consensus" in f for f in flags)

    def test_weak_buy_consensus_flagged(self):
        state = make_state(analyst_buy=3, analyst_hold=8, analyst_sell=14)
        flags = _compute_insight_flags(state)
        assert any("Weak buy consensus" in f for f in flags)

    def test_high_margin_flagged(self):
        state = make_state(profit_margins=0.30)
        flags = _compute_insight_flags(state)
        assert any("High net margin" in f for f in flags)

    def test_thin_margin_flagged(self):
        state = make_state(profit_margins=0.02)
        flags = _compute_insight_flags(state)
        assert any("Thin net margin" in f for f in flags)

    def test_high_beta_flagged(self):
        state = make_state(beta=1.8)
        flags = _compute_insight_flags(state)
        assert any("High beta" in f for f in flags)

    def test_low_beta_flagged(self):
        state = make_state(beta=0.3)
        flags = _compute_insight_flags(state)
        assert any("Low beta" in f for f in flags)

    def test_no_realtime_no_rt_flags(self):
        state = make_state(price=None)
        flags = _compute_insight_flags(state)
        # should not crash, volume flags won't appear
        assert not any("Volume spike" in f for f in flags)

    def test_upside_to_target_flagged(self):
        # price 180, target 220 → 22% upside
        state = make_state(price=180.0, analyst_target=220.0)
        flags = _compute_insight_flags(state)
        assert any("upside" in f for f in flags)

    def test_price_above_target_flagged(self):
        # price 180, target 150 → 17% above target
        state = make_state(price=180.0, analyst_target=150.0)
        flags = _compute_insight_flags(state)
        assert any("above consensus analyst target" in f for f in flags)


# ---------------------------------------------------------------------------
# _build_data_context — structural checks
# ---------------------------------------------------------------------------

class TestDataContext:
    def test_contains_dominant_signal(self):
        state = make_state(pct_change=-5.0)
        ctx = _build_data_context(state)
        assert "[DOMINANT SIGNAL]" in ctx

    def test_contains_confidence_level(self):
        state = make_state()
        ctx = _build_data_context(state)
        assert "[CONFIDENCE LEVEL]" in ctx

    def test_contains_uncertainty_flag_section(self):
        state = make_state()
        ctx = _build_data_context(state)
        assert "[UNCERTAINTY FLAG]" in ctx

    def test_contains_signal_conflict(self):
        state = make_state()
        ctx = _build_data_context(state)
        assert "[SIGNAL CONFLICT]" in ctx

    def test_no_behavioral_instructions_in_context(self):
        state = make_state()
        ctx = _build_data_context(state)
        # Data context must not contain system prompt language
        assert "USER MODE" not in ctx
        assert "STRICT RULES" not in ctx
        assert "OUTPUT FORMAT" not in ctx

    def test_currency_symbol_inr(self):
        state = make_state(currency="INR", ticker="RELIANCE", company_name="Reliance Industries")
        state["realtime_context"]["ticker"] = "RELIANCE"
        ctx = _build_data_context(state)
        assert "₹" in ctx

    def test_currency_symbol_usd(self):
        state = make_state(currency="USD")
        ctx = _build_data_context(state)
        assert "$" in ctx

    def test_conversation_history_included(self):
        state = make_state()
        state["conversation_history"] = [
            {"role": "user", "content": "What is the PE?"},
            {"role": "assistant", "content": "The PE is 28."},
        ]
        ctx = _build_data_context(state)
        assert "CONVERSATION HISTORY" in ctx

    def test_no_data_graceful(self):
        state = make_state(price=None, pe=None, eps=None, beta=None)
        state["fundamental_data"] = {}
        ctx = _build_data_context(state)
        assert "REAL-TIME DATA UNAVAILABLE" in ctx
