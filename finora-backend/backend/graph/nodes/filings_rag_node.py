"""Filings RAG node — deep fundamental context from SEC 10-K / 10-Q."""

from __future__ import annotations

import structlog
import asyncio

from backend.graph.state import FiNoraState
from backend.rag.pipeline import run_rag_branch
from backend.rag.retrieval.router import RetrievalBranch

log = structlog.get_logger()

_BRANCH = RetrievalBranch(
    intent="filings",
    collection="filings",
    use_hyde=True,  # filings benefit from abstraction
    description="SEC 10-K, 10-Q filings — risks, MD&A, financial disclosures",
    allow_global_fallback=False,
)

_TOP_K = 5


def _rewrite_query(query: str) -> str:
    """
    Section-aware steering — appends terms that match the section the query targets.
    Generic MDA bias was causing risk-factor queries to retrieve MDA chunks.
    """
    q = query.lower()
    if any(w in q for w in ("risk", "threat", "challenge", "exposure", "concern", "lawsuit", "regulatory", "litigation")):
        extra = "risk factors threats regulatory legal competitive exposure uncertainty"
    elif any(w in q for w in ("revenue", "profit", "margin", "earnings", "income", "sales", "guidance", "growth")):
        extra = "management discussion analysis revenue profit margins guidance outlook"
    elif any(w in q for w in ("business", "product", "service", "segment", "market", "competition", "strategy")):
        extra = "business description products services market segments competitive strategy"
    elif any(w in q for w in ("quantitative", "market risk", "interest rate", "forex", "hedg")):
        extra = "quantitative disclosures market risk interest rate currency hedging"
    else:
        extra = "management discussion analysis risk factors strategy revenue guidance"
    return f"{query} {extra}"


async def filings_rag_node(state: FiNoraState) -> dict:
    """
    SEC filings retrieval for stock-level context.
    SEC EDGAR is US-only — skip Indian tickers entirely.
    """

    yf_ticker = state.get("yf_ticker", "")
    if yf_ticker.endswith((".NS", ".BO")):
        return {
            "filings_chunks": [],
            "retrieval_scores": {**state.get("retrieval_scores", {}), "filings": {}},
        }

    query = state["query"]
    ticker = state.get("ticker", "")

    rewritten_query = _rewrite_query(query)

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        run_rag_branch,
        rewritten_query,
        ticker,
        _BRANCH,
    )

    chunks = [
        {
            "text": ch.text,
            "score": ch.score,
            **ch.metadata,
        }
        for ch in result.chunks[:_TOP_K]
    ]

    scores = result.retrieval_scores

    log.info(
        "filings_rag_done",
        ticker=ticker,
        chunks=len(chunks),
        scores=scores,
    )

    return {
        "filings_chunks": chunks,
        "retrieval_scores": {
            **state.get("retrieval_scores", {}),
            "filings": scores,
        },
    }
