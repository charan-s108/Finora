import asyncio
import time
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from backend.api.middleware.rate_limit import limiter
from backend.rag.ingestion.universe import universe
from backend.rag.yahoo_client import (
    fetch_balance_sheet, fetch_cashflow, fetch_company_info,
    fetch_filings, fetch_fundamentals, fetch_income_stmt,
    fetch_news, fetch_ohlcv, fetch_quote, fetch_sector_etfs,
)

log = structlog.get_logger()
router = APIRouter(tags=["stocks"])


class StockSearchResult(BaseModel):
    ticker: str
    name: str
    exchange: str
    sector: str
    country: str
    currency: str
    yf_ticker: str


class AnalystConsensus(BaseModel):
    buy: int
    hold: int
    sell: int
    avg_target: float | None


class OHLCVBar(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class NewsItem(BaseModel):
    text: str
    title: str
    source: str
    published_at: str
    url: str


class HistoricalSignal(BaseModel):
    text: str
    event_type: str
    date_range: str
    return_pct: float | None


class SimilarStock(BaseModel):
    ticker: str
    name: str
    sector: str
    exchange: str
    currency: str
    website: str | None = None


class SectorData(BaseModel):
    sector: str
    etf: str
    return_pct: float
    price: float | None = None

class FilingItem(BaseModel):
    ticker: str
    form: str
    filing_date: str
    accession_number: str
    document: str
    url: str


class FinancialPeriod(BaseModel):
    period: str
    period_type: str
    revenue: float | None = None
    net_income: float | None = None
    revenue_growth_pct: float | None = None
    profit_growth_pct: float | None = None


class FinancialPerformance(BaseModel):
    currency: str
    currency_unit: str
    annual: list[FinancialPeriod]
    quarterly: list[FinancialPeriod]
    revenue_1y_growth: float | None = None
    profit_1y_growth: float | None = None
    revenue_3y_cagr: float | None = None
    profit_3y_cagr: float | None = None


class FinancialsDetail(BaseModel):
    ticker: str
    currency: str
    currency_unit: str
    income_annual: list[dict]
    income_quarterly: list[dict]
    balance_sheet: list[dict]
    cashflow: list[dict]


class StockDetail(BaseModel):
    ticker: str
    name: str
    exchange: str
    currency: str
    sector: str | None
    industry: str | None
    country: str | None
    city: str | None
    website: str | None
    full_time_employees: int | None
    business_summary: str | None
    beta: float | None
    dividend_yield: float | None
    price: float | None
    change: float | None
    pct_change: float | None
    volume: int | None
    avg_volume_30d: int | None
    market_cap: int | None
    pe: float | None
    forward_pe: float | None
    eps: float | None
    week_52_high: float | None
    week_52_low: float | None
    analyst_consensus: AnalystConsensus | None
    ohlcv_7d: list[OHLCVBar]
    news_rag: list[NewsItem]
    historical_signals: list[HistoricalSignal]
    similar_stocks: list[SimilarStock] = []
    filings: list[FilingItem] = []
    financial_performance: FinancialPerformance | None = None


_SECTORS_CACHE: tuple[list[dict], float] | None = None
_SECTORS_TTL = 300.0  # 5 minutes


def _get_similar_stocks(current_ticker: str, sector: str | None, limit: int = 5) -> list[SimilarStock]:
    if not sector:
        return []
    all_stocks = universe.search("", limit=10000)
    similar = [
        SimilarStock(
            ticker=s["ticker"],
            name=s["name"],
            sector=s.get("sector", ""),
            exchange=s.get("exchange", ""),
            currency=s.get("currency", "USD"),
            website=s.get("website"),
        )
        for s in all_stocks
        if s.get("sector", "").lower() == sector.lower()
        and s["ticker"] != current_ticker
    ]
    return similar[:limit]


def _fmt_period_label(date_str: str, period_type: str) -> str:
    """'2024-09-30' + annual → 'FY2024'; quarterly → 'Sep '24'"""
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if period_type == "annual":
            return f"FY{dt.year}"
        return dt.strftime("%b '%y")
    except Exception:
        return date_str


def _growth_pct(curr: float | None, prev: float | None) -> float | None:
    if curr and prev and prev != 0:
        return round((curr - prev) / abs(prev) * 100, 1)
    return None


def _compute_cagr(stmts: list[dict], field: str, years: int) -> float | None:
    if len(stmts) <= years:
        return None
    end_val = stmts[0].get(field)
    start_val = stmts[years].get(field)
    if not end_val or not start_val or start_val <= 0:
        return None
    return round(((end_val / start_val) ** (1 / years) - 1) * 100, 1)


def _safe_float(val: Any) -> float | None:
    try:
        v = float(val)
        return None if v != v else v
    except (TypeError, ValueError):
        return None


def _safe_int(val: Any) -> int | None:
    try:
        v = float(val)
        return None if v != v else int(v)
    except (TypeError, ValueError):
        return None


async def _fetch_detail(yf_ticker: str, display_ticker: str) -> dict[str, Any]:
    def _blocking() -> dict[str, Any]:
        try:
            quote = fetch_quote(yf_ticker)
        except Exception:
            quote = {}
        try:
            fund = fetch_fundamentals(yf_ticker)
        except Exception:
            fund = {}
        try:
            company = fetch_company_info(yf_ticker)
        except Exception:
            company = {}

        # 7-day daily OHLCV
        ohlcv_7d: list[OHLCVBar] = []
        try:
            df = fetch_ohlcv(yf_ticker, days=7, interval="1d")
            if not df.empty:
                for dt, row in df.tail(7).iterrows():
                    ohlcv_7d.append(OHLCVBar(
                        date=str(dt.date()),
                        open=round(float(row["Open"]), 4),
                        high=round(float(row["High"]), 4),
                        low=round(float(row["Low"]), 4),
                        close=round(float(row["Close"]), 4),
                        volume=int(row["Volume"]),
                    ))
        except Exception:
            pass

        # Live news via Google News RSS
        news_rag: list[NewsItem] = []
        try:
            raw_news = fetch_news(yf_ticker, count=5)
            for n in raw_news:
                news_rag.append(NewsItem(
                    text=n.get("text", n.get("title", "")),
                    title=n.get("title", ""),
                    source=n.get("source", ""),
                    published_at=n.get("published_at", ""),
                    url=n.get("url", ""),
                ))
        except Exception as exc:
            log.warning("news_fetch_failed", ticker=yf_ticker, error=str(exc))

        # Historical signals from Qdrant (best-effort, silent fail)
        historical_signals: list[HistoricalSignal] = []
        try:
            from backend.rag.retrieval.hybrid import hybrid_search
            from backend.rag.ingestion.collections import collection_name
            chunks = hybrid_search(
                query=f"{display_ticker} historical price patterns",
                ticker=display_ticker,
                collection=collection_name("historical"),
                limit=4,
                allow_global_fallback=False,
            )
            for ch in chunks:
                meta = ch.metadata
                historical_signals.append(HistoricalSignal(
                    text=ch.text,
                    event_type=meta.get("event_type", "price_event"),
                    date_range=meta.get("date_range", meta.get("start_date", "")),
                    return_pct=_safe_float(meta.get("return_pct")),
                ))
        except Exception:
            pass  # Qdrant unavailable or ticker not in historical corpus

        filings: list[FilingItem] = []

        try:
            raw_filings = fetch_filings(yf_ticker)
            for f in raw_filings:
                filings.append(FilingItem(
                    ticker=display_ticker,
                    form=f.get("form", ""),
                    filing_date=f.get("filing_date", f.get("date", "")),
                    accession_number=f.get("accession_number", ""),
                    document=f.get("document", ""),
                    url=f.get("url", ""),
                ))
        except Exception as exc:
            log.warning("filings_fetch_failed", ticker=yf_ticker, error=str(exc))
            filings = []

        # Financial performance
        financial_performance: FinancialPerformance | None = None
        try:
            currency = "INR" if yf_ticker.endswith((".NS", ".BO")) else "USD"
            unit_divisor = 1e7 if currency == "INR" else 1e9
            currency_unit = "Cr" if currency == "INR" else "B"

            def _to_display(raw: Any) -> float | None:
                v = _safe_float(raw)
                return round(v / unit_divisor, 1) if v is not None else None

            annual_stmts = fetch_income_stmt(yf_ticker, quarterly=False)
            quarterly_stmts = fetch_income_stmt(yf_ticker, quarterly=True)

            annual_periods: list[FinancialPeriod] = []
            for i, s in enumerate(annual_stmts[:5]):
                prev = annual_stmts[i + 1] if i + 1 < len(annual_stmts) else None
                annual_periods.append(FinancialPeriod(
                    period=_fmt_period_label(s["period"], "annual"),
                    period_type="annual",
                    revenue=_to_display(s.get("revenue")),
                    net_income=_to_display(s.get("net_income")),
                    revenue_growth_pct=_growth_pct(s.get("revenue"), prev.get("revenue") if prev else None),
                    profit_growth_pct=_growth_pct(s.get("net_income"), prev.get("net_income") if prev else None),
                ))

            quarterly_periods: list[FinancialPeriod] = []
            for i, s in enumerate(quarterly_stmts[:5]):
                prev = quarterly_stmts[i + 1] if i + 1 < len(quarterly_stmts) else None
                quarterly_periods.append(FinancialPeriod(
                    period=_fmt_period_label(s["period"], "quarterly"),
                    period_type="quarterly",
                    revenue=_to_display(s.get("revenue")),
                    net_income=_to_display(s.get("net_income")),
                    revenue_growth_pct=_growth_pct(s.get("revenue"), prev.get("revenue") if prev else None),
                    profit_growth_pct=_growth_pct(s.get("net_income"), prev.get("net_income") if prev else None),
                ))

            if annual_periods or quarterly_periods:
                financial_performance = FinancialPerformance(
                    currency=currency,
                    currency_unit=currency_unit,
                    annual=annual_periods,
                    quarterly=quarterly_periods,
                    revenue_1y_growth=annual_periods[0].revenue_growth_pct if annual_periods else None,
                    profit_1y_growth=annual_periods[0].profit_growth_pct if annual_periods else None,
                    revenue_3y_cagr=_compute_cagr(annual_stmts, "revenue", 3),
                    profit_3y_cagr=_compute_cagr(annual_stmts, "net_income", 3),
                )
        except Exception as exc:
            log.warning("financial_performance_failed", ticker=yf_ticker, error=str(exc))

        ac = fund.get("analyst_consensus", {}) or {}
        consensus = AnalystConsensus(
            buy=int(ac.get("buy") or 0),
            hold=int(ac.get("hold") or 0),
            sell=int(ac.get("sell") or 0),
            avg_target=_safe_float(ac.get("avg_target")),
        )

        return {
            "price": _safe_float(quote.get("price")),
            "change": _safe_float(quote.get("change")),
            "pct_change": _safe_float(quote.get("pct_change")),
            "volume": _safe_int(quote.get("volume")),
            "avg_volume_30d": _safe_int(quote.get("avg_volume_3m")) or _safe_int(fund.get("avg_volume_3m")),
            "market_cap": _safe_int(fund.get("market_cap")) or _safe_int(quote.get("market_cap")),
            "pe": _safe_float(fund.get("pe")),
            "forward_pe": _safe_float(fund.get("forward_pe")),
            "eps": _safe_float(fund.get("eps")),
            "week_52_high": _safe_float(fund.get("week_52_high")),
            "week_52_low": _safe_float(fund.get("week_52_low")),
            "beta": _safe_float(fund.get("beta")),
            "dividend_yield": _safe_float(fund.get("dividend_yield")),
            "industry": company.get("industry") or fund.get("industry"),
            "country": company.get("country") or fund.get("country"),
            "city": company.get("city") or fund.get("city"),
            "website": company.get("website") or fund.get("website"),
            "full_time_employees": _safe_int(company.get("full_time_employees") or fund.get("full_time_employees")),
            "business_summary": company.get("business_summary") or fund.get("business_summary"),
            "analyst_consensus": consensus,
            "ohlcv_7d": ohlcv_7d,
            "news_rag": news_rag,
            "historical_signals": historical_signals,
            "filings": filings,
            "financial_performance": financial_performance,
        }

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _blocking)


class BatchQuote(BaseModel):
    ticker: str
    price: float | None
    change: float | None
    pct_change: float | None
    currency: str


@router.get("/batch-quotes", response_model=list[BatchQuote])
@limiter.limit("60/minute")
async def batch_quotes(
    request: Request,
    tickers: str = Query(..., max_length=500),
) -> list[BatchQuote]:
    """Lightweight price-only quotes for multiple tickers. Used by TickerTape."""
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()][:20]

    def _fetch_one(ticker: str) -> BatchQuote | None:
        entry = universe.get_by_ticker(ticker)
        if not entry:
            return None
        yf = entry.get("yf_ticker", ticker)
        try:
            q = fetch_quote(yf)
            return BatchQuote(
                ticker=entry["ticker"],
                price=_safe_float(q.get("price")),
                change=_safe_float(q.get("change")),
                pct_change=_safe_float(q.get("pct_change")),
                currency=entry.get("currency", "USD"),
            )
        except Exception:
            return None

    loop = asyncio.get_running_loop()
    results = await asyncio.gather(*[
        loop.run_in_executor(None, _fetch_one, t) for t in ticker_list
    ])
    return [r for r in results if r is not None]


@router.get("/sectors", response_model=list[SectorData])
@limiter.limit("30/minute")
async def get_sectors(request: Request) -> list[SectorData]:
    global _SECTORS_CACHE
    now = time.monotonic()
    if _SECTORS_CACHE and (now - _SECTORS_CACHE[1]) < _SECTORS_TTL:
        return [SectorData(**s) for s in _SECTORS_CACHE[0]]

    loop = asyncio.get_running_loop()
    raw = await loop.run_in_executor(None, fetch_sector_etfs)
    _SECTORS_CACHE = (raw, now)
    return [SectorData(**s) for s in raw]


@router.get("/search", response_model=list[StockSearchResult])
@limiter.limit("60/minute")
async def search_stocks(
    request: Request,
    q: str = Query("", max_length=100),
    limit: int = Query(10, ge=1, le=50),
) -> list[StockSearchResult]:
    results = universe.search(q, limit=limit)
    return [
        StockSearchResult(
            ticker=s["ticker"],
            name=s["name"],
            exchange=s.get("exchange", ""),
            sector=s.get("sector", ""),
            country=s.get("country", ""),
            currency=s.get("currency", "USD"),
            yf_ticker=s.get("yf_ticker", s["ticker"]),
        )
        for s in results
    ]


@router.get("/{ticker}", response_model=StockDetail)
@limiter.limit("30/minute")
async def get_stock(request: Request, ticker: str) -> StockDetail:
    entry = universe.get_by_ticker(ticker)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not in universe")

    yf_ticker = entry.get("yf_ticker", ticker)
    data: dict[str, Any] = {
        "price": None, "change": None, "pct_change": None,
        "volume": None, "avg_volume_30d": None, "market_cap": None,
        "pe": None, "forward_pe": None, "eps": None,
        "week_52_high": None, "week_52_low": None,
        "beta": None, "dividend_yield": None,
        "industry": None, "country": None, "city": None,
        "website": None, "full_time_employees": None, "business_summary": None,
        "analyst_consensus": AnalystConsensus(buy=0, hold=0, sell=0, avg_target=None),
        "ohlcv_7d": [], "news_rag": [], "historical_signals": [],
    }
    try:
        data = await _fetch_detail(yf_ticker, entry["ticker"])
    except Exception as exc:
        log.warning("yahoo_fetch_failed", ticker=yf_ticker, error=str(exc))

    sector = entry.get("sector")
    similar = _get_similar_stocks(entry["ticker"], sector)

    return StockDetail(
        ticker=entry["ticker"],
        name=entry["name"],
        exchange=entry.get("exchange", ""),
        currency=entry.get("currency", "USD"),
        sector=sector,
        similar_stocks=similar,
        **data,
    )


@router.get("/{ticker}/financials", response_model=FinancialsDetail)
@limiter.limit("20/minute")
async def get_financials(request: Request, ticker: str) -> FinancialsDetail:
    """Full Income Statement, Balance Sheet, and Cash Flow for the detail page."""
    entry = universe.get_by_ticker(ticker)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not in universe")

    yf_ticker = entry.get("yf_ticker", ticker)
    currency = "INR" if yf_ticker.endswith((".NS", ".BO")) else "USD"
    currency_unit = "Cr" if currency == "INR" else "B"

    def _blocking() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
        return (
            fetch_income_stmt(yf_ticker, quarterly=False),
            fetch_income_stmt(yf_ticker, quarterly=True),
            fetch_balance_sheet(yf_ticker),
            fetch_cashflow(yf_ticker),
        )

    loop = asyncio.get_running_loop()
    annual, quarterly, balance, cf = await loop.run_in_executor(None, _blocking)

    return FinancialsDetail(
        ticker=entry["ticker"],
        currency=currency,
        currency_unit=currency_unit,
        income_annual=annual,
        income_quarterly=quarterly,
        balance_sheet=balance,
        cashflow=cf,
    )


# Timeframe → (yahoo_range, yahoo_interval)
_TIMEFRAME_MAP: dict[str, tuple[str, str]] = {
    "1D":  ("1d",  "5m"),
    "1W":  ("5d",  "30m"),
    "1M":  ("1mo", "1d"),
    "3M":  ("3mo", "1d"),
    "6M":  ("6mo", "1d"),
    "1Y":  ("1y",  "1wk"),
    "3Y":  ("3y",  "1wk"),
    "5Y":  ("5y",  "1wk"),
    "ALL": ("20y", "1mo"),
}


class OHLCVResponse(BaseModel):
    ticker: str
    range: str
    interval: str
    bars: list[OHLCVBar]


@router.get("/{ticker}/ohlcv", response_model=OHLCVResponse)
@limiter.limit("60/minute")
async def get_ohlcv(
    request: Request,
    ticker: str,
    range: str = Query("1M", pattern="^(1D|1W|1M|3M|6M|1Y|3Y|5Y|ALL)$"),
) -> OHLCVResponse:
    entry = universe.get_by_ticker(ticker)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not in universe")

    yf_ticker = entry.get("yf_ticker", ticker)
    yahoo_range, interval = _TIMEFRAME_MAP.get(range, ("1mo", "1d"))

    def _blocking() -> list[OHLCVBar]:
        df = fetch_ohlcv(yf_ticker, interval=interval, range_str=yahoo_range)
        bars: list[OHLCVBar] = []
        if df.empty:
            return bars
        for dt, row in df.iterrows():
            try:
                bars.append(OHLCVBar(
                    date=str(dt) if range == "1D" else str(dt.date()),
                    open=round(float(row["Open"]), 4),
                    high=round(float(row["High"]), 4),
                    low=round(float(row["Low"]), 4),
                    close=round(float(row["Close"]), 4),
                    volume=int(row["Volume"]),
                ))
            except Exception:
                continue
        return bars

    loop = asyncio.get_running_loop()
    bars = await loop.run_in_executor(None, _blocking)
    return OHLCVResponse(ticker=ticker, range=range, interval=interval, bars=bars)
