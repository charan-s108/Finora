"""
Master RAG orchestrator.
Called by LangGraph nodes to execute retrieval for a given intent + ticker.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import structlog

from backend.rag.ingestion.collections import collection_name, get_client
from backend.rag.retrieval.deduplication import deduplicate_and_diversify
from backend.rag.retrieval.hybrid import RetrievedChunk, hybrid_search
from backend.rag.retrieval.hyde import generate_hyde_embedding, should_use_hyde
from backend.rag.retrieval.reranker import rerank
from backend.rag.retrieval.router import RetrievalBranch, get_branches

log = structlog.get_logger()

TOP_K = int(os.getenv("RAG_TOP_K", "8"))
CANDIDATES = TOP_K * int(os.getenv("RAG_OVER_RETRIEVE_FACTOR", "2"))


@dataclass
class RAGResult:
    chunks: list[RetrievedChunk]
    collection: str
    intent: str
    hyde_used: bool
    retrieval_scores: dict[str, Any] = field(default_factory=dict)


def run_rag_branch(
    query: str,
    ticker: str,
    branch: RetrievalBranch,
    top_k: int = TOP_K,
) -> RAGResult:
    """Execute full RAG pipeline for one intent branch."""
    client = get_client()
    col = collection_name(branch.collection)

    # HyDE: generate hypothetical doc embedding for abstract queries
    hyde_used = branch.use_hyde and bool(os.getenv("RAG_HYDE_ENABLED", "false") == "true")
    if hyde_used:
        query_vector = generate_hyde_embedding(query)
    else:
        query_vector = None

    # Hybrid retrieval: BM25 + dense, RRF-fused
    candidates = hybrid_search(
        query=query,
        ticker=ticker,
        collection=col,
        query_vector=query_vector,
        client=client,
        limit=CANDIDATES,
        allow_global_fallback=branch.allow_global_fallback,
    )

    if not candidates:
        log.debug("rag_no_candidates", ticker=ticker, intent=branch.intent, collection=col)
        return RAGResult(chunks=[], collection=col, intent=branch.intent, hyde_used=hyde_used)

    # Reranking: Cohere → BAAI fallback
    if os.getenv("RAG_RERANKER_ENABLED", "true") == "true":
        reranked = rerank(query, candidates, top_k=top_k)
    else:
        reranked = candidates[:top_k]

    # Drop chunks below minimum relevance (Cohere 0–1 range only; BGE logits skipped)
    # Fallback: if threshold wipes all results, keep top-2 — empty context is worse than low-score context
    min_score = float(os.getenv("RAG_MIN_RELEVANCE_SCORE", "0.05"))
    if reranked and 0.0 <= reranked[0].score <= 1.0:
        filtered = [c for c in reranked if c.score >= min_score]
        reranked = filtered if filtered else reranked[:2]

    # Deduplication + MMR diversity
    final = deduplicate_and_diversify(query, reranked, top_k=top_k)

    scores = {
        "candidates": len(candidates),
        "after_rerank": len(reranked),
        "after_dedup": len(final),
        "top_score": final[0].score if final else 0.0,
    }
    log.info("rag_branch_done", ticker=ticker, intent=branch.intent, **scores)

    return RAGResult(
        chunks=final,
        collection=col,
        intent=branch.intent,
        hyde_used=hyde_used,
        retrieval_scores=scores,
    )


def run_rag(
    query: str,
    ticker: str,
    intents: list[str],
    top_k: int = TOP_K,
) -> list[RAGResult]:
    """
    Run all RAG branches for the given intents in sequence.
    LangGraph handles parallel execution across graph nodes.
    """
    branches = get_branches(intents)  # type: ignore[arg-type]
    results: list[RAGResult] = []

    for branch in branches:
        try:
            result = run_rag_branch(query, ticker, branch, top_k=top_k)
            results.append(result)
        except Exception as exc:
            log.error("rag_branch_failed", intent=branch.intent, ticker=ticker, error=str(exc))
            results.append(RAGResult(
                chunks=[],
                collection=collection_name(branch.collection),
                intent=branch.intent,
                hyde_used=False,
            ))

    return results


def format_context(results: list[RAGResult]) -> str:
    """Render retrieved chunks into the fusion prompt context string."""
    sections: list[str] = []
    for result in results:
        if not result.chunks:
            continue
        label = result.intent.upper().replace("_", " ")
        lines = [f"[{label} CONTEXT — {len(result.chunks)} sources]"]
        for i, chunk in enumerate(result.chunks, 1):
            meta = chunk.metadata
            source = meta.get("source", meta.get("url", "unknown"))
            date = meta.get("published_at", meta.get("start_date", ""))
            lines.append(f"[{i}] {source} ({date}): {chunk.text}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)
