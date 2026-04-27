"""Historical RAG node — HyDE → hybrid retrieval → rerank → dedup → append to historical_chunks."""
from __future__ import annotations

import structlog

from backend.graph.state import FiNoraState
from backend.rag.pipeline import run_rag_branch
from backend.rag.retrieval.router import RetrievalBranch

log = structlog.get_logger()

_BRANCH = RetrievalBranch(
    intent="historical",
    collection="historical",
    use_hyde=True,
    description="20yr OHLCV event patterns, earnings history, technicals",
    allow_global_fallback=True,
)


async def historical_rag_node(state: FiNoraState) -> dict:
    if "historical" not in state.get("intents", []):
        return {"historical_chunks": []}

    query = state["query"]
    ticker = state.get("ticker", "")

    import asyncio
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, run_rag_branch, query, ticker, _BRANCH)

    chunks = [
        {"text": ch.text, "score": ch.score, **ch.metadata}
        for ch in result.chunks
    ]
    scores = result.retrieval_scores
    log.info("historical_rag_done", ticker=ticker, chunks=len(chunks), scores=scores)
    return {
        "historical_chunks": chunks,
        "retrieval_scores": {**state.get("retrieval_scores", {}), "historical": scores},
    }
