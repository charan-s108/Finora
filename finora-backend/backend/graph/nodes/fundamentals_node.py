"""Fundamentals node — Yahoo Finance quoteSummary via curl_cffi."""
from __future__ import annotations

import asyncio
import time

import structlog

from backend.graph.state import FiNoraState
from backend.rag.yahoo_client import fetch_fundamentals, fetch_sector_etfs

log = structlog.get_logger()

_FUNDAMENTALS_CACHE: dict[str, tuple[dict, float]] = {}
_SECTOR_CACHE: tuple[list[dict], float] | None = None
_CACHE_TTL = 300.0  # 5 minutes


def _get_cached_fundamentals(yf_ticker: str) -> dict | None:
    entry = _FUNDAMENTALS_CACHE.get(yf_ticker)
    if entry and (time.monotonic() - entry[1]) < _CACHE_TTL:
        return entry[0]
    return None


def _set_cached_fundamentals(yf_ticker: str, data: dict) -> None:
    _FUNDAMENTALS_CACHE[yf_ticker] = (data, time.monotonic())


def _get_similar_stocks(ticker: str, sector: str | None) -> list[dict]:
    if not sector:
        return []
    try:
        from backend.rag.ingestion.universe import universe
        all_stocks = universe.search("", limit=10000)
        similar = [
            {"ticker": s["ticker"], "name": s["name"],
             "sector": s.get("sector", ""), "exchange": s.get("exchange", ""),
             "currency": s.get("currency", "USD")}
            for s in all_stocks
            if s.get("sector", "").lower() == sector.lower() and s["ticker"] != ticker
        ]
        return similar[:8]
    except Exception:
        return []


def _fetch_sector_context(ticker: str, sector: str | None) -> dict:
    global _SECTOR_CACHE
    now = time.monotonic()

    etfs: list[dict] = []
    if _SECTOR_CACHE and (now - _SECTOR_CACHE[1]) < _CACHE_TTL:
        etfs = _SECTOR_CACHE[0]
    else:
        try:
            etfs = fetch_sector_etfs()
            _SECTOR_CACHE = (etfs, now)
        except Exception:
            etfs = []

    similar = _get_similar_stocks(ticker, sector)

    # Find the ETF for this stock's sector
    sector_etf: dict | None = None
    if sector:
        for etf in etfs:
            if etf.get("sector", "").lower() == sector.lower():
                sector_etf = etf
                break

    return {
        "sector": sector,
        "sector_etf": sector_etf,
        "all_sector_etfs": etfs,
        "similar_stocks": similar,
    }


async def fundamentals_node(state: FiNoraState) -> dict:
    intents = state.get("intents", [])
    has_fundamental = "fundamental" in intents
    has_comparative = "comparative" in intents

    if not has_fundamental and not has_comparative:
        return {"fundamental_data": None, "sector_context": None}

    ticker = state.get("ticker", "")
    yf_ticker = state.get("yf_ticker", ticker)
    if not ticker:
        return {"fundamental_data": None, "sector_context": None}

    result: dict = {"fundamental_data": None, "sector_context": None}

    # Fetch fundamentals if needed
    if has_fundamental:
        cached = _get_cached_fundamentals(yf_ticker)
        if cached:
            log.debug("fundamentals_cache_hit", ticker=ticker)
            result["fundamental_data"] = cached
        else:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, fetch_fundamentals, yf_ticker)
            data["ticker"] = ticker
            _set_cached_fundamentals(yf_ticker, data)
            log.info("fundamentals_node_done", ticker=ticker, yf_ticker=yf_ticker, pe=data.get("pe"))
            result["fundamental_data"] = data

    # Fetch sector context if comparative intent present
    if has_comparative:
        # Get sector from fundamentals data or state
        fd = result.get("fundamental_data") or {}
        sector = fd.get("sector") or state.get("sector")

        # If no fundamentals fetched yet, get sector from universe
        if not sector:
            try:
                from backend.rag.ingestion.universe import universe
                entry = universe.get_by_ticker(ticker)
                sector = (entry or {}).get("sector")
            except Exception:
                sector = None

        loop = asyncio.get_running_loop()
        sector_ctx = await loop.run_in_executor(None, _fetch_sector_context, ticker, sector)
        result["sector_context"] = sector_ctx
        log.info("sector_context_fetched", ticker=ticker, sector=sector,
                 similar_count=len(sector_ctx.get("similar_stocks", [])),
                 etfs_count=len(sector_ctx.get("all_sector_etfs", [])))

    return result
