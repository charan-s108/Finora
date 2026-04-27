"""
Hybrid retrieval: BM25 (sparse) + Qdrant (dense) fused via Reciprocal Rank Fusion.
BM25 is built on-the-fly from Qdrant scroll results filtered by ticker.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from rank_bm25 import BM25Okapi

from backend.rag.embedder import embed
from backend.rag.ingestion.collections import get_client, collection_name

log = structlog.get_logger()

TOP_K = int(os.getenv("RAG_TOP_K", "8"))
OVER_RETRIEVE = int(os.getenv("RAG_OVER_RETRIEVE_FACTOR", "2"))
CANDIDATES = TOP_K * OVER_RETRIEVE   # 16 by default
RRF_K = 60


@dataclass
class RetrievedChunk:
    id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


def _ticker_filter(ticker: str) -> Filter:
    return Filter(must=[FieldCondition(key="ticker", match=MatchValue(value=ticker))])


def _scroll_collection(client: QdrantClient, col: str, ticker: str) -> list[dict]:
    """Fetch chunks from a collection for BM25. ticker='' means no filter (global)."""
    all_points: list[dict] = []
    offset = None
    scroll_filter = _ticker_filter(ticker) if ticker else None
    while True:
        results, offset = client.scroll(
            collection_name=col,
            scroll_filter=scroll_filter,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for r in results:
            all_points.append({"id": str(r.id), "payload": r.payload or {}})
        if offset is None:
            break
    return all_points


def _rrf(ranked_lists: list[list[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion over lists of doc IDs."""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])


def hybrid_search(
    query: str,
    ticker: str,
    collection: str,
    query_vector: list[float] | None = None,
    client: QdrantClient | None = None,
    limit: int = CANDIDATES,
    allow_global_fallback: bool = False,
) -> list[RetrievedChunk]:
    """
    BM25 + dense vector search, RRF-fused.
    query_vector: pre-computed embedding (e.g. from HyDE). If None, embeds query.
    allow_global_fallback: if True, retry without ticker filter when ticker yields no results.
                           Set False for news (unrelated articles worse than no context).
    """
    c = client or get_client()
    vec = query_vector if query_vector is not None else embed(query)

    # --- Dense retrieval (qdrant-client >=1.9 uses query_points, not search) ---
    ticker_filter = _ticker_filter(ticker) if ticker else None
    qr = c.query_points(
        collection_name=collection,
        query=vec,
        query_filter=ticker_filter,
        limit=limit,
        with_payload=True,
    )
    dense_results = qr.points

    # Fallback: only for collections where cross-ticker context is valid (e.g. historical)
    if not dense_results and ticker and allow_global_fallback:
        log.info("rag_ticker_fallback_global", ticker=ticker, collection=collection)
        qr = c.query_points(
            collection_name=collection,
            query=vec,
            limit=limit,
            with_payload=True,
        )
        dense_results = qr.points
    dense_id_order = [str(r.id) for r in dense_results]
    id_to_chunk: dict[str, RetrievedChunk] = {
        str(r.id): RetrievedChunk(
            id=str(r.id),
            text=r.payload.get("text", "") if r.payload else "",
            score=float(r.score),
            metadata={k: v for k, v in (r.payload or {}).items() if k != "text"},
        )
        for r in dense_results
    }

    # --- Sparse retrieval (BM25 over ticker corpus) ---
    corpus_points = _scroll_collection(c, collection, ticker)
    if not corpus_points and ticker and allow_global_fallback:
        corpus_points = _scroll_collection(c, collection, "")  # global fallback

    sparse_id_order: list[str] = []
    if corpus_points:
        corpus_texts = [p["payload"].get("text", "") for p in corpus_points]
        tokenized = [t.lower().split() for t in corpus_texts]
        bm25 = BM25Okapi(tokenized)
        scores = bm25.get_scores(query.lower().split())
        ranked_indices = sorted(range(len(scores)), key=lambda i: -scores[i])

        for idx in ranked_indices[:limit]:
            pt = corpus_points[idx]
            doc_id = pt["id"]
            sparse_id_order.append(doc_id)
            if doc_id not in id_to_chunk:
                id_to_chunk[doc_id] = RetrievedChunk(
                    id=doc_id,
                    text=pt["payload"].get("text", ""),
                    score=float(scores[idx]),
                    metadata={k: v for k, v in pt["payload"].items() if k != "text"},
                )

    # --- RRF fusion ---
    fused = _rrf([dense_id_order, sparse_id_order])

    results: list[RetrievedChunk] = []
    for doc_id, rrf_score in fused[:limit]:
        if doc_id in id_to_chunk:
            chunk = id_to_chunk[doc_id]
            chunk.score = rrf_score
            results.append(chunk)

    return results
