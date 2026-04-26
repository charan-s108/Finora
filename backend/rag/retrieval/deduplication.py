"""
Semantic deduplication + MMR (Maximal Marginal Relevance).

Step 1: Remove near-duplicates (cosine similarity > 0.92).
Step 2: MMR — balance relevance (λ=0.6) vs diversity (1-λ=0.4).
"""
from __future__ import annotations

import os

import numpy as np

from rag.embedder import embed, embed_batch
from rag.retrieval.hybrid import RetrievedChunk

DEDUP_THRESHOLD = float(os.getenv("RAG_DEDUP_THRESHOLD", "0.92"))
MMR_LAMBDA = float(os.getenv("RAG_MMR_LAMBDA", "0.6"))


def _cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


def semantic_dedup(
    chunks: list[RetrievedChunk],
    threshold: float = DEDUP_THRESHOLD,
) -> list[RetrievedChunk]:
    """Remove chunks whose text is >threshold cosine similar to an already-kept chunk."""
    if not chunks:
        return []

    texts = [ch.text for ch in chunks]
    embeddings = embed_batch(texts)

    kept: list[RetrievedChunk] = []
    kept_embs: list[list[float]] = []

    for chunk, emb in zip(chunks, embeddings):
        is_dup = any(_cosine(emb, ke) >= threshold for ke in kept_embs)
        if not is_dup:
            kept.append(chunk)
            kept_embs.append(emb)

    return kept


def mmr_select(
    query: str,
    chunks: list[RetrievedChunk],
    lambda_: float = MMR_LAMBDA,
    k: int | None = None,
) -> list[RetrievedChunk]:
    """
    Maximal Marginal Relevance selection.
    lambda_=0.6: 60% relevance weight, 40% diversity weight.
    """
    if not chunks:
        return []

    top_k = k or len(chunks)
    query_emb = np.array(embed(query))
    doc_embs = np.array(embed_batch([ch.text for ch in chunks]))

    # Relevance scores: cosine(query, doc)
    norms = np.linalg.norm(doc_embs, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    doc_embs_norm = doc_embs / norms
    query_norm = query_emb / (np.linalg.norm(query_emb) or 1)
    relevance = doc_embs_norm @ query_norm  # shape: (n,)

    selected: list[int] = []
    remaining = list(range(len(chunks)))

    for _ in range(min(top_k, len(chunks))):
        if not remaining:
            break

        if not selected:
            # Pick highest relevance first
            best = max(remaining, key=lambda i: relevance[i])
        else:
            # MMR score: λ·rel(i) - (1-λ)·max_sim(i, selected)
            sel_embs = doc_embs_norm[selected]
            scores = []
            for i in remaining:
                sim_to_selected = float(np.max(doc_embs_norm[i] @ sel_embs.T))
                mmr_score = lambda_ * relevance[i] - (1 - lambda_) * sim_to_selected
                scores.append((i, mmr_score))
            best = max(scores, key=lambda x: x[1])[0]

        selected.append(best)
        remaining.remove(best)

    return [chunks[i] for i in selected]


def deduplicate_and_diversify(
    query: str,
    chunks: list[RetrievedChunk],
    top_k: int,
    dedup_threshold: float = DEDUP_THRESHOLD,
    mmr_lambda: float = MMR_LAMBDA,
) -> list[RetrievedChunk]:
    """Full dedup pipeline: semantic dedup → MMR select."""
    deduped = semantic_dedup(chunks, threshold=dedup_threshold)
    return mmr_select(query, deduped, lambda_=mmr_lambda, k=top_k)
