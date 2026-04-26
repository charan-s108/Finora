"""
Unified Yahoo Finance client using curl_cffi Chrome TLS impersonation.

Replaces yfinance library for all data fetching. Works for all exchanges
(US, NSE India .NS, BSE .BO, LSE .L, etc.) without IP blocks.

Session is a module-level singleton — one Chrome TLS session shared across
all requests. Cookie/crumb lifecycle managed automatically.
"""
from __future__ import annotations

import os
import time
from functools import lru_cache

import pandas as pd
import structlog

log = structlog.get_logger()

try:
    from curl_cffi import requests as cffi_requests
    _session = cffi_requests.Session(impersonate="chrome124")
    _AVAILABLE = True
except ImportError:
    _session = None
    _AVAILABLE = False
    log.error("curl_cffi_missing", fix="pip install curl_cffi")

_BASE1 = "https://query1.finance.yahoo.com"
_BASE2 = "https://query2.finance.yahoo.com"

_crumb: str | None = None
_crumb_ts: float = 0.0
_CRUMB_TTL = 3600  # seconds


def _get_crumb() -> str:
    global _crumb, _crumb_ts
    if _crumb and time.time() - _crumb_ts < _CRUMB_TTL:
        return _crumb
    try:
        r = _session.get(f"{_BASE2}/v1/test/getcrumb", timeout=10)
        if r.status_code == 200 and r.text.strip():
            _crumb = r.text.strip()
            _crumb_ts = time.time()
            return _crumb
    except Exception as exc:
        log.warning("crumb_fetch_failed", error=str(exc))
    return ""


def _warm_session(ticker: str) -> None:
    """One chart request primes session cookies; crumb then works."""
    try:
        _session.get(
            f"{_BASE1}/v8/finance/chart/{ticker}",
            params={"range": "5d", "interval": "1d"},
            timeout=10,
        )
    except Exception:
        pass


# ── OHLCV ──────────────────────────────────────────────────────────────────

def fetch_ohlcv(
    ticker: str,
    years: int = 20,
    interval: str = "1wk",
    days: int | None = None,
    range_str: str | None = None,
) -> pd.DataFrame:
    """OHLCV for any ticker. Pass range_str (e.g. '1mo','3mo','1y') or days for intraday."""
    if not _AVAILABLE:
        return pd.DataFrame()

    url = f"{_BASE1}/v8/finance/chart/{ticker}"
    if not range_str:
        range_str = f"{days}d" if days else f"{min(years, 20)}y"
    params = {
        "range": range_str,
        "interval": interval,
        "includePrePost": "false",
        "events": "history",
    }
    try:
        r = _session.get(url, params=params, timeout=20)
        if r.status_code != 200:
            log.warning("ohlcv_http_error", ticker=ticker, status=r.status_code)
            return pd.DataFrame()

        data = r.json()
        chart_result = data.get("chart", {}).get("result", [])
        if not chart_result:
            return pd.DataFrame()

        chart = chart_result[0]
        timestamps = chart.get("timestamp", [])
        if not timestamps:
            return pd.DataFrame()

        quote = chart.get("indicators", {}).get("quote", [{}])[0]
        adj_list = chart.get("indicators", {}).get("adjclose", [{}])
        adjclose = adj_list[0].get("adjclose", []) if adj_list else []

        rows = []
        for i, ts in enumerate(timestamps):
            close_val = (
                adjclose[i] if i < len(adjclose) and adjclose[i]
                else (quote.get("close") or [None])[i] if i < len(quote.get("close") or []) else None
            )
            if close_val is None:
                continue
            rows.append({
                "Open": (quote.get("open") or [None])[i] if i < len(quote.get("open") or []) else None,
                "High": (quote.get("high") or [None])[i] if i < len(quote.get("high") or []) else None,
                "Low": (quote.get("low") or [None])[i] if i < len(quote.get("low") or []) else None,
                "Close": close_val,
                "Volume": (quote.get("volume") or [0])[i] or 0,
            })

        if not rows:
            return pd.DataFrame()

        idx = pd.to_datetime(timestamps[: len(rows)], unit="s", utc=True).tz_localize(None)
        return pd.DataFrame(rows, index=idx).dropna(subset=["Close"])

    except Exception as exc:
        log.warning("ohlcv_fetch_failed", ticker=ticker, error=str(exc))
        return pd.DataFrame()


# ── Real-time quote ────────────────────────────────────────────────────────

def fetch_quote(ticker: str) -> dict:
    """Real-time price, change, volume from v8 chart (1d/2m interval)."""
    if not _AVAILABLE:
        return {"ticker": ticker, "error": "curl_cffi unavailable"}

    try:
        r = _session.get(
            f"{_BASE1}/v8/finance/chart/{ticker}",
            params={"range": "1d", "interval": "2m", "includePrePost": "false"},
            timeout=15,
        )
        data = r.json()
        chart_result = data.get("chart", {}).get("result", [])
        if not chart_result:
            return {"ticker": ticker, "price": None}

        meta = chart_result[0].get("meta", {})
        price = meta.get("regularMarketPrice")
        prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
        change = round(price - prev_close, 4) if price and prev_close else None
        pct_change = round(change / prev_close * 100, 2) if change and prev_close else None

        # Intraday OHLC from timestamps
        quote = chart_result[0].get("indicators", {}).get("quote", [{}])[0]
        opens = [v for v in (quote.get("open") or []) if v]
        highs = [v for v in (quote.get("high") or []) if v]
        lows = [v for v in (quote.get("low") or []) if v]
        volumes = [v for v in (quote.get("volume") or []) if v]

        return {
            "ticker": ticker,
            "price": price,
            "prev_close": prev_close,
            "change": change,
            "pct_change": pct_change,
            "volume": sum(volumes) if volumes else meta.get("regularMarketVolume"),
            "avg_volume_3m": meta.get("averageDailyVolume3Month"),
            "market_cap": meta.get("marketCap"),
            "open": opens[0] if opens else None,
            "high": max(highs) if highs else None,
            "low": min(lows) if lows else None,
            "currency": meta.get("currency", "USD"),
            "exchange": meta.get("exchangeName"),
            "timestamp": meta.get("regularMarketTime"),
        }
    except Exception as exc:
        log.warning("quote_fetch_failed", ticker=ticker, error=str(exc))
        return {"ticker": ticker, "error": str(exc)}


# ── Live news ─────────────────────────────────────────────────────────────

def fetch_news(ticker: str, count: int = 8) -> list[dict]:
    """
    Live news for a ticker via Google News RSS (no API key needed).
    Handles both Indian (.NS / .BO) and US/global tickers.
    """
    if not _AVAILABLE:
        return []
    try:
        import datetime as _dt
        import xml.etree.ElementTree as _ET

        # Build locale-aware query
        is_india = ticker.endswith((".NS", ".BO"))
        base = ticker.replace(".NS", "").replace(".BO", "")
        if is_india:
            query = f"{base} NSE stock India"
            params = {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
        else:
            query = f"{base} stock"
            params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}

        r = _session.get("https://news.google.com/rss/search", params=params, timeout=10)
        if r.status_code != 200:
            log.warning("news_rss_error", ticker=ticker, status=r.status_code)
            return []

        root = _ET.fromstring(r.content)
        items = root.findall(".//item")[:count]
        results: list[dict] = []
        for item in items:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            source = item.findtext("source", "Google News")
            pub_date = item.findtext("pubDate", "")
            description = item.findtext("description", "")
            # Parse date: "Fri, 24 Apr 2026 07:30:00 GMT"
            try:
                dt = _dt.datetime.strptime(pub_date[:16].strip(), "%a, %d %b %Y")
                date_str = dt.strftime("%Y-%m-%d")
            except Exception:
                date_str = pub_date[:10]
            results.append({
                "text": f"{title}. {description}".strip(". ") if description else title,
                "url": link,
                "title": title,
                "source": source,
                "published_at": date_str,
                "ticker": ticker,
                "live": True,
            })
        log.info("news_rss_ok", ticker=ticker, count=len(results))
        return results
    except Exception as exc:
        log.warning("news_fetch_failed", ticker=ticker, error=str(exc))
        return []


# ── Fundamentals ───────────────────────────────────────────────────────────

def fetch_fundamentals(ticker: str) -> dict:
    """PE, EPS, margins, analyst consensus via quoteSummary API."""
    if not _AVAILABLE:
        return {"ticker": ticker, "error": "curl_cffi unavailable"}

    try:
        # Warm session + get crumb on first call
        _warm_session(ticker)
        crumb = _get_crumb()
    except Exception as exc:
        log.warning("fundamentals_session_failed", ticker=ticker, error=str(exc))
        return {"ticker": ticker, "error": str(exc)}

    modules = "summaryDetail,financialData,defaultKeyStatistics,recommendationTrend"
    params: dict = {"modules": modules}
    if crumb:
        params["crumb"] = crumb

    try:
        r = _session.get(
            f"{_BASE1}/v10/finance/quoteSummary/{ticker}",
            params=params,
            timeout=15,
        )
        data = r.json()
        result = data.get("quoteSummary", {}).get("result", [])
        if not result:
            return {"ticker": ticker}

        item = result[0]
        sd = item.get("summaryDetail", {})
        fd = item.get("financialData", {})
        ks = item.get("defaultKeyStatistics", {})
        recs = item.get("recommendationTrend", {}).get("trend", [])

        buy = hold = sell = 0
        if recs:
            r0 = recs[0]
            buy = r0.get("strongBuy", 0) + r0.get("buy", 0)
            hold = r0.get("hold", 0)
            sell = r0.get("sell", 0) + r0.get("strongSell", 0)

        def _raw(d: dict, key: str):
            v = d.get(key)
            if isinstance(v, dict):
                return v.get("raw")
            return v

        return {
            "ticker": ticker,
            "pe": _raw(sd, "trailingPE"),
            "forward_pe": _raw(sd, "forwardPE"),
            "eps": _raw(ks, "trailingEps"),
            "revenue": _raw(fd, "totalRevenue"),
            "revenue_growth": _raw(fd, "revenueGrowth"),
            "gross_margin": _raw(fd, "grossMargins"),
            "operating_margin": _raw(fd, "operatingMargins"),
            "net_margin": _raw(fd, "profitMargins"),
            "debt_to_equity": _raw(fd, "debtToEquity"),
            "current_ratio": _raw(fd, "currentRatio"),
            "roe": _raw(fd, "returnOnEquity"),
            "market_cap": _raw(sd, "marketCap"),
            "avg_volume_3m": _raw(sd, "averageVolume"),
            "dividend_yield": _raw(sd, "dividendYield"),
            "beta": _raw(sd, "beta"),
            "week_52_high": _raw(sd, "fiftyTwoWeekHigh"),
            "week_52_low": _raw(sd, "fiftyTwoWeekLow"),
            "analyst_consensus": {"buy": buy, "hold": hold, "sell": sell,
                                   "avg_target": _raw(fd, "targetMeanPrice")},
        }
    except Exception as exc:
        log.warning("fundamentals_fetch_failed", ticker=ticker, error=str(exc))
        return {"ticker": ticker, "error": str(exc)}


def fetch_company_info(ticker: str) -> dict:
    """Company profile: business summary, industry, country, employees, website."""
    if not _AVAILABLE:
        return {}
    try:
        _warm_session(ticker)
        crumb = _get_crumb()
        params: dict = {"modules": "assetProfile"}
        if crumb:
            params["crumb"] = crumb
        r = _session.get(
            f"{_BASE1}/v10/finance/quoteSummary/{ticker}",
            params=params,
            timeout=12,
        )
        data = r.json()
        result = data.get("quoteSummary", {}).get("result", [])
        if not result:
            return {}
        ap = result[0].get("assetProfile", {})
        if not ap:
            return {}
        return {
            "industry": ap.get("industry"),
            "country": ap.get("country"),
            "city": ap.get("city"),
            "website": ap.get("website"),
            "full_time_employees": ap.get("fullTimeEmployees"),
            "business_summary": ap.get("longBusinessSummary"),
        }
    except Exception as exc:
        log.warning("company_info_fetch_failed", ticker=ticker, error=str(exc))
        return {}
