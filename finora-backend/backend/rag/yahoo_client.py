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

import threading
_crumb_lock = threading.Lock()

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


def _get_valid_crumb(ticker: str) -> str:
    global _crumb, _crumb_ts

    if _crumb and time.time() - _crumb_ts < _CRUMB_TTL:
        return _crumb

    with _crumb_lock:
        # double-check inside lock
        if _crumb and time.time() - _crumb_ts < _CRUMB_TTL:
            return _crumb

        _warm_session(ticker)

        try:
            r = _session.get(f"{_BASE2}/v1/test/getcrumb", timeout=10)
            if r.status_code == 200 and r.text.strip():
                _crumb = r.text.strip()
                _crumb_ts = time.time()
                return _crumb
        except Exception as exc:
            log.warning("crumb_fetch_failed", error=str(exc))

    raise RuntimeError("Failed to obtain Yahoo crumb")


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
        if price is not None and prev_close is not None:
            change = round(price - prev_close, 4)
            pct_change = round(change / prev_close * 100, 2)
        else:
            change = None
            pct_change = None

        # Intraday OHLC from timestamps
        quote = chart_result[0].get("indicators", {}).get("quote", [{}])[0]
        opens = [v for v in (quote.get("open") or []) if v is not None]
        highs = [v for v in (quote.get("high") or []) if v is not None]
        lows = [v for v in (quote.get("low") or []) if v is not None]
        volumes = [v for v in (quote.get("volume") or []) if v is not None]

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
        import xml.etree.ElementTree as _ET
        from email.utils import parsedate_to_datetime

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
            title = item.findtext("title", "") or ""
            link = item.findtext("link", "") or ""
            source = item.findtext("source", "Google News") or "Google News"
            pub_date = item.findtext("pubDate", "") or ""
            description = item.findtext("description", "") or ""

            try:
                dt = parsedate_to_datetime(pub_date)
                date_str = dt.strftime("%Y-%m-%d")
            except Exception:
                date_str = pub_date[:10] if pub_date else None

            results.append({
                "text": f"{title}. {description}".strip(". "),
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
    global _crumb

    if not _AVAILABLE:
        return {"ticker": ticker, "error": "curl_cffi unavailable"}

    for attempt in range(2):
        try:
            crumb = _get_valid_crumb(ticker)
            break
        except Exception as exc:
            log.warning("crumb_retry", ticker=ticker, error=str(exc))
            _crumb = None

            if attempt == 1:
                return {"ticker": ticker, "error": "crumb init failed"}

    modules = "summaryDetail,financialData,defaultKeyStatistics,recommendationTrend,assetProfile,summaryProfile,price,quoteType"
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
        result = (data.get("quoteSummary") or {}).get("result") or []
        result = [r for r in result if r]

        if not result:
            log.warning("empty_fundamentals", ticker=ticker)

            _crumb = None
            _warm_session(ticker)

            try:
                crumb = _get_valid_crumb(ticker)
                params["crumb"] = crumb

                r = _session.get(
                    f"{_BASE1}/v10/finance/quoteSummary/{ticker}",
                    params=params,
                    timeout=15,
                )
                data = r.json()
                result = data.get("quoteSummary", {}).get("result", [])
            except Exception as exc:
                log.warning("fundamentals_retry_failed", ticker=ticker, error=str(exc))
                return {"ticker": ticker, "error": "retry failed"}

            if not result:
                return {"ticker": ticker, "error": "no data after retry"}

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
        crumb = _get_valid_crumb(ticker)
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
        ap = (
            result[0].get("assetProfile")
            or result[0].get("summaryProfile")
            or {}
        )
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


# ── Sector ETF performance ─────────────────────────────────────────────────

_SECTOR_ETFS: list[tuple[str, str]] = [
    ("XLK",  "Technology"),
    ("XLV",  "Healthcare"),
    ("XLF",  "Financials"),
    ("XLE",  "Energy"),
    ("XLY",  "Consumer Disc."),
    ("XLP",  "Consumer Staples"),
    ("XLB",  "Materials"),
    ("XLI",  "Industrials"),
    ("XLU",  "Utilities"),
    ("XLRE", "Real Estate"),
    ("XLC",  "Comm. Services"),
    ("SOXX", "Semiconductors"),
]


def fetch_sector_etfs() -> list[dict]:
    """
    Fetch daily % change for 12 US sector ETFs.
    Returns [{sector, etf, return_pct, price}].
    """
    results = []
    for etf, label in _SECTOR_ETFS:
        try:
            q = fetch_quote(etf)
            pct = q.get("pct_change")
            price = q.get("price")
            if pct is not None:
                results.append({
                    "sector": label,
                    "etf": etf,
                    "return_pct": round(float(pct), 2),
                    "price": round(float(price), 2) if price else None,
                })
        except Exception:
            continue
    return results


# ── SEC Filings (EDGAR) ────────────────────────────────────────────────

def fetch_filings(ticker: str, count: int = 10) -> list[dict]:
    """
    Fetch latest SEC filings (10-K, 10-Q, 8-K etc.) from EDGAR for a ticker.
    Works via company CIK lookup → filings feed.
    """

    if not _AVAILABLE:
        return []

    try:
        import json
        import xml.etree.ElementTree as ET

        headers = {
            "User-Agent": "FinoraAI/1.0 (contact: support@finora.ai)"
        }

        # 1. Get ticker → CIK mapping
        mapping_url = "https://www.sec.gov/files/company_tickers.json"
        r = _session.get(mapping_url, headers=headers, timeout=15)

        if r.status_code != 200:
            return []

        data = r.json()

        cik = None
        ticker = ticker.upper()

        for _, v in data.items():
            if v.get("ticker", "").upper() == ticker:
                cik = str(v.get("cik_str")).zfill(10)
                break

        if not cik:
            return []

        # 2. Pull filings feed
        feed_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        r = _session.get(feed_url, headers=headers, timeout=15)

        if r.status_code != 200:
            return []

        filings = r.json().get("filings", {}).get("recent", {})

        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        accession = filings.get("accessionNumber", [])
        primary_docs = filings.get("primaryDocument", [])

        results = []

        for i in range(min(count, len(forms))):
            results.append({
                "ticker": ticker,
                "form": forms[i],
                "filing_date": dates[i],
                "accession_number": accession[i],
                "document": primary_docs[i],
                "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession[i].replace('-', '')}/{primary_docs[i]}",
            })

        return results

    except Exception as exc:
        log.warning("filings_fetch_failed", ticker=ticker, error=str(exc))
        return []
