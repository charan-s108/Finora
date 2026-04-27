"""Real-time data node — Yahoo Finance v8 via curl_cffi Chrome TLS impersonation."""
from __future__ import annotations

import asyncio
import time

import structlog

from backend.graph.state import FiNoraState
from backend.rag.yahoo_client import fetch_ohlcv, fetch_quote

log = structlog.get_logger()

_PATTERNS_CACHE: dict[str, tuple[list[dict], float]] = {}
_PATTERNS_TTL = 300.0  # 5 minutes


def _fetch_historical_patterns(ticker: str) -> list[dict]:
    """
    Fetch historical context from Qdrant — same query the dashboard uses —
    so chat has historical data regardless of intent routing.
    Returns up to 2 pattern chunks, empty list on any failure. Cached 5 min.
    """
    cached = _PATTERNS_CACHE.get(ticker)
    if cached and (time.monotonic() - cached[1]) < _PATTERNS_TTL:
        log.debug("historical_patterns_cache_hit", ticker=ticker)
        return cached[0]

    try:
        from backend.rag.retrieval.hybrid import hybrid_search
        from backend.rag.ingestion.collections import collection_name
        chunks = hybrid_search(
            query=f"{ticker} historical price patterns earnings volatility",
            ticker=ticker,
            collection=collection_name("historical"),
            limit=2,
            allow_global_fallback=False,
        )
        results = []
        for ch in chunks:
            meta = ch.metadata if hasattr(ch, "metadata") else {}
            results.append({
                "text": ch.text if hasattr(ch, "text") else str(ch),
                "event_type": meta.get("event_type", "price_event"),
                "date_range": meta.get("date_range", meta.get("start_date", "")),
                "return_pct": meta.get("return_pct"),
            })
        _PATTERNS_CACHE[ticker] = (results, time.monotonic())
        return results
    except Exception as exc:
        log.debug("historical_patterns_fetch_skipped", ticker=ticker, error=str(exc))
        return []


def _fetch_realtime(ticker: str) -> dict:
    quote = fetch_quote(ticker)

    # 1d intraday bars (5m interval, last 12 bars for streaming chart)
    df_intraday = fetch_ohlcv(ticker, days=1, interval="5m")
    intraday: list[dict] = []
    if not df_intraday.empty:
        for dt, row in df_intraday.tail(12).iterrows():
            intraday.append({
                "time": str(dt),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            })

    # 30d daily bars for monthly price chart
    df_30d = fetch_ohlcv(ticker, range_str="1mo", interval="1d")
    monthly: list[dict] = []
    if not df_30d.empty:
        for dt, row in df_30d.iterrows():
            monthly.append({
                "date": str(dt)[:10],
                "close": round(float(row["Close"]), 4),
            })

    return {
        "price": quote.get("price"),
        "change": quote.get("change"),
        "pct_change": quote.get("pct_change"),
        "volume": quote.get("volume"),
        "avg_volume_30d": quote.get("avg_volume_3m"),
        "market_cap": quote.get("market_cap"),
        "week_52_high": None,
        "week_52_low": None,
        "open": quote.get("open"),
        "intraday": intraday,
        "monthly": monthly,
    }


async def realtime_node(state: FiNoraState) -> dict:
    ticker = state.get("ticker", "")
    yf_ticker = state.get("yf_ticker", ticker)
    if not ticker:
        return {"realtime_context": None}

    loop = asyncio.get_running_loop()

    # Fetch realtime + historical patterns concurrently
    realtime_task = loop.run_in_executor(None, _fetch_realtime, yf_ticker)
    historical_task = loop.run_in_executor(None, _fetch_historical_patterns, ticker)

    data, historical_patterns = await asyncio.gather(realtime_task, historical_task)

    data["ticker"] = ticker
    # Always inject historical patterns — chat has parity with dashboard regardless of intent
    data["historical_patterns"] = historical_patterns

    log.info(
        "realtime_node_done",
        ticker=ticker,
        price=data.get("price"),
        historical_patterns=len(historical_patterns),
    )
    return {"realtime_context": data}
