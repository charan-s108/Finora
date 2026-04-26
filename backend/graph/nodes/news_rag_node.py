"""News RAG node — HyDE → hybrid retrieval → rerank → dedup → append to news_chunks.
Falls back to live Yahoo Finance news when ticker has no indexed docs.
"""
from __future__ import annotations

import asyncio

import structlog

from graph.state import FiNoraState
from rag.pipeline import run_rag_branch
from rag.retrieval.router import RetrievalBranch

log = structlog.get_logger()

_BRANCH = RetrievalBranch(
    intent="news",
    collection="news",
    use_hyde=True,
    description="News articles, analyst reports, press releases",
    allow_global_fallback=False,
)

_TOP_K = 8


async def news_rag_node(state: FiNoraState) -> dict:
    if "news" not in state.get("intents", []) and "comparative" not in state.get("intents", []):
        return {"news_chunks": []}

    query = state["query"]
    ticker = state.get("ticker", "")
    yf_ticker = state.get("yf_ticker", ticker)

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, run_rag_branch, query, ticker, _BRANCH)

    chunks = [
        {"text": ch.text, "score": ch.score, **ch.metadata}
        for ch in result.chunks
    ]

    if not chunks and (ticker or yf_ticker):
        # No indexed news — fall back to live Yahoo Finance headlines
        from rag.yahoo_client import fetch_news
        live = await loop.run_in_executor(None, fetch_news, yf_ticker or ticker, _TOP_K)
        if live:
            chunks = live
            log.info("news_live_fallback", ticker=ticker, yf_ticker=yf_ticker, count=len(chunks))
        else:
            log.info("news_no_data", ticker=ticker, yf_ticker=yf_ticker)

    scores = result.retrieval_scores
    log.info("news_rag_done", ticker=ticker, chunks=len(chunks), source="rag" if result.chunks else "live")
    return {
        "news_chunks": chunks,
        "retrieval_scores": {**state.get("retrieval_scores", {}), "news": scores},
    }
