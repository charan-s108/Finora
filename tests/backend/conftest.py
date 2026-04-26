"""Shared fixtures for Finora backend tests."""
import sys
import os

# Make backend importable without installing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))


def make_state(
    query: str = "what is happening",
    ticker: str = "AAPL",
    company_name: str = "Apple Inc.",
    currency: str = "USD",
    user_mode: str = "insight",
    intents: list | None = None,
    price: float | None = 180.0,
    pct_change: float | None = 0.0,
    volume: int | None = 25_000_000,
    avg_volume_30d: int | None = 25_000_000,
    week_52_high: float | None = 200.0,
    week_52_low: float | None = 150.0,
    pe: float | None = 28.0,
    forward_pe: float | None = 25.0,
    eps: float | None = 6.43,
    beta: float | None = 1.2,
    profit_margins: float | None = 0.22,
    market_cap: float | None = 2_800_000_000_000,
    analyst_buy: int = 20,
    analyst_hold: int = 8,
    analyst_sell: int = 2,
    analyst_target: float | None = 210.0,
    news_chunks: list | None = None,
    historical_chunks: list | None = None,
) -> dict:
    """Build a minimal FiNoraState dict for testing."""
    realtime = None
    if price is not None:
        realtime = {
            "ticker": ticker,
            "price": price,
            "change": price * (pct_change / 100) if pct_change else 0.0,
            "pct_change": pct_change,
            "volume": volume,
            "avg_volume_30d": avg_volume_30d,
            "week_52_high": week_52_high,
            "week_52_low": week_52_low,
        }

    fundamental = {
        "pe": pe,
        "forward_pe": forward_pe,
        "eps": eps,
        "beta": beta,
        "profit_margins": profit_margins,
        "market_cap": market_cap,
        "analyst_target": analyst_target,
        "analyst_consensus": {
            "buy": analyst_buy,
            "hold": analyst_hold,
            "sell": analyst_sell,
            "avg_target": analyst_target,
        },
    }

    return {
        "query": query,
        "ticker": ticker,
        "yf_ticker": ticker,
        "company_name": company_name,
        "currency": currency,
        "user_mode": user_mode,
        "session_id": "test-session",
        "conversation_history": [],
        "intents": intents if intents is not None else ["real_time", "fundamental", "news", "historical"],
        "guardrail_flags": [],
        "guardrail_blocked": False,
        "realtime_context": realtime,
        "news_chunks": news_chunks or [],
        "historical_chunks": historical_chunks or [],
        "fundamental_data": fundamental,
        "fused_context": "",
        "response": "",
        "citations": [],
        "confidence_score": 0.0,
        "disclaimer_text": "",
        "trace_id": "test-0001",
        "retrieval_scores": {},
    }
