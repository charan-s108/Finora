"""News RAG node — live Google RSS (dashboard-parity) + Qdrant supplementary context."""
from __future__ import annotations

import asyncio

import structlog

from backend.graph.state import FiNoraState
from backend.rag.pipeline import run_rag_branch
from backend.rag.retrieval.router import RetrievalBranch

log = structlog.get_logger()

_BRANCH = RetrievalBranch(
    intent="news",
    collection="news",
    use_hyde=False,
    description="News articles, analyst reports, press releases",
    allow_global_fallback=False,
)

_TOP_K = 4  # Qdrant supplementary chunks (already capped in fusion)
_LIVE_COUNT = 5  # Google RSS headlines — same source as dashboard


async def news_rag_node(state: FiNoraState) -> dict:
    if "news" not in state.get("intents", []) and "comparative" not in state.get("intents", []):
        return {"news_chunks": []}

    query = state["query"]
    ticker = state.get("ticker", "")
    yf_ticker = state.get("yf_ticker", ticker)

    loop = asyncio.get_running_loop()
    from backend.rag.yahoo_client import fetch_news

    # Always fetch live Google RSS first — same source the dashboard displays.
    # This guarantees LLM sees the same headlines the user is looking at.
    live_task = loop.run_in_executor(None, fetch_news, yf_ticker or ticker, _LIVE_COUNT)
    rag_task = loop.run_in_executor(None, run_rag_branch, query, ticker, _BRANCH)

    live_news, result = await asyncio.gather(live_task, rag_task)

    # Qdrant chunks — supplementary historical/older context
    qdrant_chunks = [
        {"text": ch.text, "score": ch.score, **ch.metadata}
        for ch in result.chunks
    ]

    # Deduplicate: drop Qdrant chunks whose title appears in live headlines
    live_titles = {n.get("title", "").lower()[:60] for n in live_news}
    qdrant_chunks = [
        ch for ch in qdrant_chunks
        if ch.get("title", ch.get("text", ""))[:60].lower() not in live_titles
    ]

    # Live RSS headlines first (highest priority = same as dashboard)
    # Qdrant supplementary second
    chunks = list(live_news) + qdrant_chunks

    scores = result.retrieval_scores
    log.info(
        "news_rag_done",
        ticker=ticker,
        live=len(live_news),
        qdrant=len(qdrant_chunks),
        total=len(chunks),
    )
    return {
        "news_chunks": chunks,
        "retrieval_scores": {**state.get("retrieval_scores", {}), "news": scores},
    }
