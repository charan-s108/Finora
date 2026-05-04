"""Financials RAG node — structured financial statement context from Qdrant."""

from __future__ import annotations

import asyncio

import structlog

from backend.graph.state import FiNoraState
from backend.rag.pipeline import run_rag_branch
from backend.rag.retrieval.router import RetrievalBranch

log = structlog.get_logger()

_BRANCH = RetrievalBranch(
    intent="financials",  # type: ignore[arg-type]
    collection="financials",
    use_hyde=False,  # structured numeric data — HyDE adds noise
    description="Financial statements — income, balance sheet, cashflow for US + Indian stocks",
    allow_global_fallback=False,
)

_TOP_K = 4


async def financials_rag_node(state: FiNoraState) -> dict:
    """
    Retrieve pre-ingested financial statement chunks from Qdrant finora_financials.
    Works for ALL stocks (US + Indian) — no ticker skip needed.
    """
    query = state["query"]
    ticker = state.get("ticker", "")

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        run_rag_branch,
        query,
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
        "financials_rag_done",
        ticker=ticker,
        chunks=len(chunks),
        scores=scores,
    )

    return {
        "financials_chunks": chunks,
        "retrieval_scores": {
            **state.get("retrieval_scores", {}),
            "financials": scores,
        },
    }
