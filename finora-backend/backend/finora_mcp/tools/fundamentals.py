"""MCP tool: get_fundamentals — PE, EPS, revenue, margins, analyst consensus."""
from __future__ import annotations

from backend.rag.yahoo_client import fetch_fundamentals


def get_fundamentals(ticker: str) -> dict:
    """PE, EPS, revenue, margins, debt, analyst consensus, price targets."""
    return fetch_fundamentals(ticker)
