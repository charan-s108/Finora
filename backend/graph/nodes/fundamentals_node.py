"""Fundamentals node — Yahoo Finance quoteSummary via curl_cffi."""
from __future__ import annotations

import asyncio

import structlog

from graph.state import FiNoraState
from rag.yahoo_client import fetch_fundamentals

log = structlog.get_logger()


async def fundamentals_node(state: FiNoraState) -> dict:
    if "fundamental" not in state.get("intents", []):
        return {"fundamental_data": None}

    ticker = state.get("ticker", "")
    yf_ticker = state.get("yf_ticker", ticker)
    if not ticker:
        return {"fundamental_data": None}

    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, fetch_fundamentals, yf_ticker)
    data["ticker"] = ticker
    log.info("fundamentals_node_done", ticker=ticker, yf_ticker=yf_ticker, pe=data.get("pe"))
    return {"fundamental_data": data}
