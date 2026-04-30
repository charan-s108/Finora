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
    Light steering → forces retrieval toward high-value sections
    without breaking user intent.
    """
    return (
        f"{query} "
        "management discussion analysis risks growth strategy revenue margins guidance"
    )


async def filings_rag_node(state: FiNoraState) -> dict:
    """
    SEC filings retrieval for stock-level context.
    """

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
