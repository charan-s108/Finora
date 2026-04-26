"""MCP tool: search_news_rag — hybrid search over news + SEC filings."""
from __future__ import annotations


def search_news_rag(ticker: str, query: str, days: int = 30, top_k: int = 8) -> list[dict]:
    """Hybrid search over news + SEC filings. Reranked, deduplicated."""
    from rag.pipeline import run_rag_branch

    results = run_rag_branch(
        query=query,
        ticker=ticker,
        collection_key="news",
        use_hyde=True,
        top_k=top_k,
    )
    return [
        {
            "text": r.text,
            "ticker": r.metadata.get("ticker"),
            "source": r.metadata.get("source"),
            "published_at": r.metadata.get("published_at"),
            "url": r.metadata.get("url"),
            "sentiment_score": r.metadata.get("sentiment_score"),
            "score": round(r.score, 4) if r.score else None,
        }
        for r in results
    ]
