"""
Ingest financial statements (Income, Balance Sheet, Cash Flow) for all stocks
→ natural language text chunks → Qdrant (finora_financials).

Works for both US (USD) and Indian (.NS/.BO, INR) tickers.
Run once via scripts/ingest_financials.py, then refresh quarterly.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from backend.rag.embedder import embed_batch
from backend.rag.ingestion.collections import collection_name, get_client
from backend.rag.yahoo_client import fetch_balance_sheet, fetch_cashflow, fetch_income_stmt

log = structlog.get_logger()


def _fmt_val(raw: float | None, currency: str) -> str:
    if raw is None:
        return "N/A"
    if currency == "INR":
        return f"₹{raw / 1e7:,.0f} Cr"
    if abs(raw) >= 1e12:
        return f"${raw / 1e12:.2f}T"
    if abs(raw) >= 1e9:
        return f"${raw / 1e9:.1f}B"
    return f"${raw / 1e6:.0f}M"


def _growth(curr: float | None, prev: float | None) -> float | None:
    if curr and prev and prev != 0:
        return round((curr - prev) / abs(prev) * 100, 1)
    return None


def _period_label(date_str: str, period_type: str) -> str:
    """'2024-09-30' + annual → 'FY2024'; quarterly → 'Sep '24'"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if period_type == "annual":
            return f"FY{dt.year}"
        return dt.strftime("%b '%y")
    except Exception:
        return date_str


def _income_chunk_text(
    ticker: str,
    stmt: dict,
    prev: dict | None,
    currency: str,
    label: str,
) -> str:
    period_type = "Quarterly" if stmt["period_type"] == "quarterly" else "Annual"
    rev = stmt.get("revenue")
    net = stmt.get("net_income")
    gp = stmt.get("gross_profit")
    op = stmt.get("operating_income")
    exp = stmt.get("total_expenses")

    rev_growth = _growth(rev, prev.get("revenue") if prev else None)
    net_growth = _growth(net, prev.get("net_income") if prev else None)

    parts = [f"{ticker} {label} {period_type} Income Statement:"]
    parts.append(f"Revenue {_fmt_val(rev, currency)}" + (f" ({rev_growth:+.1f}% YoY)" if rev_growth is not None else "") + ".")
    parts.append(f"Net Profit {_fmt_val(net, currency)}" + (f" ({net_growth:+.1f}% YoY)" if net_growth is not None else "") + ".")
    if gp is not None:
        gm = round(gp / rev * 100, 1) if rev else None
        parts.append(f"Gross Profit {_fmt_val(gp, currency)}" + (f" (Margin {gm}%)" if gm else "") + ".")
    if op is not None:
        om = round(op / rev * 100, 1) if rev else None
        parts.append(f"Operating Income {_fmt_val(op, currency)}" + (f" (Margin {om}%)" if om else "") + ".")
    if exp is not None:
        parts.append(f"Total Operating Expenses {_fmt_val(exp, currency)}.")
    return " ".join(parts)


def _balance_chunk_text(ticker: str, stmt: dict, currency: str, label: str) -> str:
    assets = stmt.get("total_assets")
    liab = stmt.get("total_liabilities")
    equity = stmt.get("total_equity")
    cash = stmt.get("cash")
    ltd = stmt.get("long_term_debt")
    ca = stmt.get("current_assets")
    cl = stmt.get("current_liabilities")

    parts = [f"{ticker} {label} Balance Sheet:"]
    if assets is not None:
        parts.append(f"Total Assets {_fmt_val(assets, currency)}.")
    if liab is not None:
        parts.append(f"Total Liabilities {_fmt_val(liab, currency)}.")
    if equity is not None:
        parts.append(f"Shareholder Equity {_fmt_val(equity, currency)}.")
    if cash is not None:
        parts.append(f"Cash & Equivalents {_fmt_val(cash, currency)}.")
    if ltd is not None:
        parts.append(f"Long-term Debt {_fmt_val(ltd, currency)}.")
    if ca and cl and cl != 0:
        cr = round(ca / cl, 2)
        parts.append(f"Current Ratio {cr}x.")
    return " ".join(parts)


def _cashflow_chunk_text(ticker: str, stmt: dict, currency: str, label: str) -> str:
    op_cf = stmt.get("operating_cashflow")
    capex = stmt.get("capex")
    inv_cf = stmt.get("investing_cashflow")
    fin_cf = stmt.get("financing_cashflow")

    parts = [f"{ticker} {label} Cash Flow Statement:"]
    if op_cf is not None:
        parts.append(f"Operating Cash Flow {_fmt_val(op_cf, currency)}.")
    if capex is not None:
        fcf = op_cf - abs(capex) if op_cf is not None else None
        parts.append(f"Capital Expenditure {_fmt_val(capex, currency)}.")
        if fcf is not None:
            parts.append(f"Free Cash Flow {_fmt_val(fcf, currency)}.")
    if inv_cf is not None:
        parts.append(f"Investing Cash Flow {_fmt_val(inv_cf, currency)}.")
    if fin_cf is not None:
        parts.append(f"Financing Cash Flow {_fmt_val(fin_cf, currency)}.")
    return " ".join(parts)


def ingest_ticker(
    ticker: str,
    yf_ticker: str,
    currency: str = "USD",
    client: QdrantClient | None = None,
    max_periods: int = 5,
) -> int:
    """
    Fetch financial statements for one ticker and upsert to Qdrant finora_financials.
    Returns total chunk count ingested.
    """
    c = client or get_client()
    col = collection_name("financials")

    annual = fetch_income_stmt(yf_ticker, quarterly=False)
    quarterly = fetch_income_stmt(yf_ticker, quarterly=True)
    balance = fetch_balance_sheet(yf_ticker)
    cashflow = fetch_cashflow(yf_ticker)

    if not annual and not quarterly:
        log.warning("financials_no_data", ticker=ticker, yf_ticker=yf_ticker)
        return 0

    points: list[PointStruct] = []
    texts: list[str] = []
    metas: list[dict] = []

    # Annual income statements
    for i, stmt in enumerate(annual[:max_periods]):
        prev = annual[i + 1] if i + 1 < len(annual) else None
        label = _period_label(stmt["period"], "annual")
        text = _income_chunk_text(ticker, stmt, prev, currency, label)
        texts.append(text)
        metas.append({
            "ticker": ticker,
            "yf_ticker": yf_ticker,
            "period": stmt["period"],
            "period_label": label,
            "period_type": "annual",
            "statement_type": "income",
            "currency": currency,
            "revenue": stmt.get("revenue"),
            "net_income": stmt.get("net_income"),
            "data_type": "financial_statement",
            "text": text,
        })

    # Quarterly income statements (last max_periods quarters)
    for i, stmt in enumerate(quarterly[:max_periods]):
        prev = quarterly[i + 1] if i + 1 < len(quarterly) else None
        label = _period_label(stmt["period"], "quarterly")
        text = _income_chunk_text(ticker, stmt, prev, currency, label)
        texts.append(text)
        metas.append({
            "ticker": ticker,
            "yf_ticker": yf_ticker,
            "period": stmt["period"],
            "period_label": label,
            "period_type": "quarterly",
            "statement_type": "income",
            "currency": currency,
            "revenue": stmt.get("revenue"),
            "net_income": stmt.get("net_income"),
            "data_type": "financial_statement",
            "text": text,
        })

    # Annual balance sheets
    for stmt in balance[:max_periods]:
        label = _period_label(stmt["period"], "annual")
        text = _balance_chunk_text(ticker, stmt, currency, label)
        texts.append(text)
        metas.append({
            "ticker": ticker,
            "yf_ticker": yf_ticker,
            "period": stmt["period"],
            "period_label": label,
            "period_type": "annual",
            "statement_type": "balance_sheet",
            "currency": currency,
            "data_type": "financial_statement",
            "text": text,
        })

    # Annual cash flows
    for stmt in cashflow[:max_periods]:
        label = _period_label(stmt["period"], "annual")
        text = _cashflow_chunk_text(ticker, stmt, currency, label)
        texts.append(text)
        metas.append({
            "ticker": ticker,
            "yf_ticker": yf_ticker,
            "period": stmt["period"],
            "period_label": label,
            "period_type": "annual",
            "statement_type": "cashflow",
            "currency": currency,
            "data_type": "financial_statement",
            "text": text,
        })

    if not texts:
        return 0

    vectors = embed_batch(texts)

    for i, (meta, vec) in enumerate(zip(metas, vectors)):
        uid = str(uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"{ticker}:{meta['statement_type']}:{meta['period']}:{meta['period_type']}",
        ))
        points.append(PointStruct(id=uid, vector=vec, payload=meta))

    c.upsert(collection_name=col, points=points)
    log.info(
        "financials_ingest_done",
        ticker=ticker,
        chunks=len(points),
        annual_income=len(annual[:max_periods]),
        quarterly_income=len(quarterly[:max_periods]),
        balance_sheets=len(balance[:max_periods]),
        cashflows=len(cashflow[:max_periods]),
    )
    return len(points)
