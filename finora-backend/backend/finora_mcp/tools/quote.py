"""MCP tool: get_realtime_quote — live price, volume, intraday OHLC."""
from __future__ import annotations

from backend.rag.yahoo_client import fetch_quote


def get_realtime_quote(ticker: str) -> dict:
    """Live price, volume, intraday OHLC, market status. Works for US + Indian stocks."""
    return fetch_quote(ticker)
