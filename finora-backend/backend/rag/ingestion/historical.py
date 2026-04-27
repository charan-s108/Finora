"""
Ingest OHLCV history → FinancialEventChunker → Qdrant (finora_historical).

Primary source: Yahoo Finance v8 chart API via curl_cffi Chrome TLS impersonation.
  - Works for ALL tickers: US, Indian (.NS), European, etc.
  - No API key required. No IP blocks (TLS fingerprint bypasses bot detection).
  - 20yr weekly history, adjusted close prices.

Fallback: Polygon.io (US tickers, ~2yr free tier, requires POLYGON_API_KEY).
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from datetime import date, timedelta

import pandas as pd
import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from backend.rag.chunking.financial import FinancialEventChunker
from backend.rag.embedder import embed_batch
from backend.rag.ingestion.collections import collection_name, get_client

log = structlog.get_logger()

_chunker = FinancialEventChunker()

# Shared curl_cffi session — Chrome TLS fingerprint impersonation
# This is what Yahoo Finance requires in 2024 to avoid 429/empty responses.
# Standard requests.Session only sends HTTP headers; Yahoo also checks TLS fingerprint.
try:
    from curl_cffi import requests as cffi_requests
    _cffi_session = cffi_requests.Session(impersonate="chrome124")
    _CFFI_AVAILABLE = True
except ImportError:
    _cffi_session = None
    _CFFI_AVAILABLE = False
    log.warning("curl_cffi_not_installed", hint="pip install curl_cffi")


# ── Yahoo Finance v8 chart API (primary, universal) ────────────────────────

def _fetch_ohlcv_yahoo(yf_ticker: str, years: int = 20) -> pd.DataFrame:
    """
    Fetch weekly OHLCV via Yahoo Finance v8 chart API with curl_cffi TLS impersonation.
    Works universally for US and Indian stocks. No API key needed.
    """
    if not _CFFI_AVAILABLE or _cffi_session is None:
        return pd.DataFrame()

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_ticker}"
    params = {
        "range": f"{min(years, 20)}y",
        "interval": "1wk",
        "includePrePost": "false",
        "events": "history",
    }

    try:
        r = _cffi_session.get(url, params=params, timeout=20)
        if r.status_code != 200:
            log.warning("yahoo_v8_http_error", ticker=yf_ticker, status=r.status_code)
            return pd.DataFrame()

        data = r.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            log.warning("yahoo_v8_no_result", ticker=yf_ticker)
            return pd.DataFrame()

        chart = result[0]
        timestamps = chart.get("timestamp", [])
        if not timestamps:
            return pd.DataFrame()

        quote = chart.get("indicators", {}).get("quote", [{}])[0]
        adj_list = chart.get("indicators", {}).get("adjclose", [{}])
        adjclose = adj_list[0].get("adjclose", []) if adj_list else []

        rows = []
        for i, ts in enumerate(timestamps):
            close_val = adjclose[i] if i < len(adjclose) and adjclose[i] else (
                (quote.get("close") or [])[i] if i < len(quote.get("close") or []) else None
            )
            if close_val is None:
                continue
            rows.append({
                "Open": (quote.get("open") or [None])[i] if i < len(quote.get("open") or []) else None,
                "High": (quote.get("high") or [None])[i] if i < len(quote.get("high") or []) else None,
                "Low": (quote.get("low") or [None])[i] if i < len(quote.get("low") or []) else None,
                "Close": close_val,
                "Volume": (quote.get("volume") or [0])[i] or 0 if i < len(quote.get("volume") or []) else 0,
            })

        if not rows:
            return pd.DataFrame()

        idx = pd.to_datetime(timestamps[:len(rows)], unit="s", utc=True).tz_localize(None)
        df = pd.DataFrame(rows, index=idx).dropna(subset=["Close"])
        log.info("yahoo_v8_fetch_ok", ticker=yf_ticker, rows=len(df))
        return df

    except Exception as exc:
        log.warning("yahoo_v8_fetch_failed", ticker=yf_ticker, error=str(exc))
        return pd.DataFrame()


# ── Polygon.io fallback (US tickers, ~2yr free tier) ──────────────────────

def _fetch_ohlcv_polygon(poly_ticker: str, years: int = 20) -> pd.DataFrame:
    """Polygon.io fallback. Free tier: ~2yr lookback, 5 calls/min."""
    api_key = os.getenv("POLYGON_API_KEY", "")
    if not api_key:
        return pd.DataFrame()

    max_lookback = min(years, 2)
    end_dt = date.today()
    start_dt = end_dt - timedelta(days=max_lookback * 365)

    try:
        from polygon import RESTClient
        time.sleep(13)  # Polygon free tier: 5 calls/min = 12s minimum gap
        client = RESTClient(api_key=api_key)
        aggs = list(client.get_aggs(
            poly_ticker, 1, "week",
            str(start_dt), str(end_dt),
            limit=5000, adjusted=True,
        ))
        if not aggs:
            return pd.DataFrame()

        rows = [
            {
                "Date": pd.Timestamp.fromtimestamp(a.timestamp / 1000, tz="UTC").tz_localize(None),
                "Open": a.open, "High": a.high, "Low": a.low,
                "Close": a.close, "Volume": a.volume or 0,
            }
            for a in aggs
        ]
        df = pd.DataFrame(rows).set_index("Date").sort_index()
        log.info("polygon_fetch_ok", ticker=poly_ticker, rows=len(df))
        return df

    except Exception as exc:
        log.warning("polygon_fetch_failed", ticker=poly_ticker, error=str(exc))
        return pd.DataFrame()


# ── Main fetch: Yahoo primary → Polygon fallback ───────────────────────────

def _fetch_ohlcv(yf_ticker: str, years: int = 20) -> pd.DataFrame:
    # Yahoo Finance v8 with Chrome TLS impersonation — works for all tickers
    df = _fetch_ohlcv_yahoo(yf_ticker, years)
    if not df.empty:
        return df

    # Polygon fallback (US tickers only, 2yr max on free tier)
    poly_ticker = yf_ticker.split(".")[0].upper()
    log.info("yahoo_failed_trying_polygon", ticker=yf_ticker)
    return _fetch_ohlcv_polygon(poly_ticker, years)


# ── Ingest functions ───────────────────────────────────────────────────────

def ingest_ticker(
    ticker: str,
    yf_ticker: str,
    years: int = 20,
    client: QdrantClient | None = None,
) -> int:
    c = client or get_client()
    col = collection_name("historical")

    log.info("historical_ingest_start", ticker=ticker, yf_ticker=yf_ticker)

    try:
        df = _fetch_ohlcv(yf_ticker, years)
    except Exception as exc:
        log.error("historical_fetch_failed", ticker=ticker, error=str(exc))
        return 0

    if df.empty:
        log.warning("historical_empty", ticker=ticker)
        return 0

    # Flatten MultiIndex columns (yfinance sometimes returns these)
    if hasattr(df.columns, "get_level_values"):
        try:
            df.columns = df.columns.get_level_values(0)
        except Exception:
            pass

    chunks = _chunker.chunk(df, ticker)
    if not chunks:
        log.warning("historical_no_events", ticker=ticker, rows=len(df))
        return 0

    texts = [ch.text for ch in chunks]
    vectors = embed_batch(texts)

    points = [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{ticker}:{ch.metadata['date_range']}")),
            vector=vec,
            payload={**ch.metadata, "text": ch.text, "source": "historical_ohlcv"},
        )
        for ch, vec in zip(chunks, vectors)
    ]

    c.upsert(collection_name=col, points=points)
    log.info("historical_ingest_done", ticker=ticker, chunks=len(points))
    return len(points)


async def ingest_ticker_async(ticker: str, yf_ticker: str, years: int = 20) -> int:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, ingest_ticker, ticker, yf_ticker, years)


def ingest_universe(
    stocks: list[dict],
    years: int = 20,
    delay_seconds: float = 0.5,
) -> dict[str, int]:
    """Sequential ingest. curl_cffi handles rate limiting gracefully."""
    client = get_client()
    results: dict[str, int] = {}
    total = len(stocks)

    for i, s in enumerate(stocks):
        ticker = s["ticker"]
        yf_ticker = s.get("yf_ticker", ticker)
        log.info("historical_universe_progress", done=i, total=total, ticker=ticker)
        try:
            results[ticker] = ingest_ticker(ticker, yf_ticker, years, client)
        except Exception as exc:
            log.error("historical_universe_failed", ticker=ticker, error=str(exc))
            results[ticker] = 0
        if i < total - 1:
            time.sleep(delay_seconds)

    return results
