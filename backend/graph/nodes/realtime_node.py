"""Real-time data node — Yahoo Finance v8 via curl_cffi Chrome TLS impersonation."""
from __future__ import annotations

import asyncio

import structlog

from graph.state import FiNoraState
from rag.yahoo_client import fetch_ohlcv, fetch_quote

log = structlog.get_logger()


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

    # Always fetch realtime data — charts need it regardless of intent
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, _fetch_realtime, yf_ticker)
    data["ticker"] = ticker
    log.info("realtime_node_done", ticker=ticker, yf_ticker=yf_ticker, price=data.get("price"))
    return {"realtime_context": data}
