"""MCP tool: screen_stocks + get_stock_universe."""
from __future__ import annotations

from typing import Optional


def screen_stocks(
    sector: Optional[str] = None,
    min_pe: Optional[float] = None,
    max_pe: Optional[float] = None,
    country: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """Screen S&P 500 + NIFTY 50 universe by criteria."""
    from backend.rag.ingestion.universe import StockUniverse
    from backend.rag.yahoo_client import fetch_fundamentals

    u = StockUniverse()
    stocks = u.stocks

    if sector:
        stocks = [s for s in stocks if (s.get("sector") or "").lower() == sector.lower()]
    if country:
        stocks = [s for s in stocks if (s.get("country") or "").lower() == country.lower()]

    if (min_pe is not None or max_pe is not None) and stocks:
        filtered = []
        for s in stocks[:50]:
            try:
                fund = fetch_fundamentals(s.get("yf_ticker", s["ticker"]))
                pe = fund.get("pe")
                if pe is None:
                    continue
                if min_pe is not None and pe < min_pe:
                    continue
                if max_pe is not None and pe > max_pe:
                    continue
                filtered.append({**s, "pe": round(pe, 2)})
                if len(filtered) >= limit:
                    break
            except Exception:
                continue
        return filtered

    return [
        {"ticker": s["ticker"], "name": s.get("name"), "sector": s.get("sector"),
         "country": s.get("country"), "exchange": s.get("exchange")}
        for s in stocks[:limit]
    ]


def get_stock_universe(query: Optional[str] = None, limit: int = 10) -> list[dict]:
    """Fuzzy search ~555 stocks by name or ticker."""
    from backend.rag.ingestion.universe import StockUniverse

    u = StockUniverse()
    results = u.search(query, limit=limit) if query else u.stocks[:limit]
    return [
        {"ticker": s["ticker"], "name": s.get("name"), "sector": s.get("sector"),
         "country": s.get("country"), "exchange": s.get("exchange"),
         "yf_ticker": s.get("yf_ticker", s["ticker"])}
        for s in results
    ]
