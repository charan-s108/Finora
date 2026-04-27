"""MCP tool: search_historical_rag — semantic + BM25 hybrid over 20yr OHLCV event chunks."""
from __future__ import annotations


def search_historical_rag(ticker: str, query: str, years: int = 20, top_k: int = 5) -> list[dict]:
    """Semantic + BM25 hybrid search over 20yr OHLCV event chunks. Reranked results."""
    from backend.rag.pipeline import run_rag_branch

    results = run_rag_branch(
        query=query,
        ticker=ticker,
        collection_key="historical",
        use_hyde=True,
        top_k=top_k,
    )
    return [
        {
            "text": r.text,
            "ticker": r.metadata.get("ticker"),
            "date_range": r.metadata.get("date_range"),
            "event_type": r.metadata.get("event_type"),
            "return_pct": r.metadata.get("return_pct"),
            "score": round(r.score, 4) if r.score else None,
        }
        for r in results
    ]
