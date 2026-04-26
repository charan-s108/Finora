"""
Cross-encoder reranking.
Primary:  Cohere rerank-english-v3.0 (API)
Fallback: BAAI/bge-reranker-base (local HuggingFace)
"""
from __future__ import annotations

import os
from functools import lru_cache

import structlog

from rag.retrieval.hybrid import RetrievedChunk

log = structlog.get_logger()

TOP_K = int(os.getenv("RAG_TOP_K", "8"))
_COHERE_MODEL = "rerank-english-v3.0"


@lru_cache(maxsize=1)
def _get_bge_reranker():
    from sentence_transformers import CrossEncoder
    model = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
    log.info("bge_reranker_loaded", model=model)
    return CrossEncoder(model)


def _rerank_cohere(query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    import cohere
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise RuntimeError("COHERE_API_KEY not set")

    co = cohere.ClientV2(api_key=api_key)
    response = co.rerank(
        model=_COHERE_MODEL,
        query=query,
        documents=[ch.text for ch in chunks],
        top_n=top_k,
    )
    reranked: list[RetrievedChunk] = []
    for result in response.results:
        chunk = chunks[result.index]
        chunk.score = float(result.relevance_score)
        reranked.append(chunk)
    return reranked


def _rerank_bge(query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    reranker = _get_bge_reranker()
    pairs = [(query, ch.text) for ch in chunks]
    scores = reranker.predict(pairs)
    scored = sorted(zip(chunks, scores), key=lambda x: -float(x[1]))
    result = []
    for chunk, score in scored[:top_k]:
        chunk.score = float(score)
        result.append(chunk)
    return result


def rerank(
    query: str,
    chunks: list[RetrievedChunk],
    top_k: int = TOP_K,
) -> list[RetrievedChunk]:
    """
    Rerank chunks by relevance to query.
    Tries Cohere first; falls back to BAAI/bge-reranker-base.
    """
    if not chunks:
        return []

    provider = os.getenv("RERANKER_PROVIDER", "cohere").lower()

    if provider == "cohere":
        try:
            reranked = _rerank_cohere(query, chunks, top_k)
            log.debug("reranker_cohere_ok", chunks_in=len(chunks), chunks_out=len(reranked))
            return reranked
        except Exception as exc:
            log.warning("cohere_rerank_failed_bge_fallback", error=str(exc))

    # BGE fallback (or primary when RERANKER_PROVIDER=bge)
    reranked = _rerank_bge(query, chunks, top_k)
    log.debug("reranker_bge_ok", chunks_in=len(chunks), chunks_out=len(reranked))
    return reranked
