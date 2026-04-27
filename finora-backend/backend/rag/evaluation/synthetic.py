"""Generate synthetic QA pairs from Qdrant chunks for RAGAS evaluation."""
from __future__ import annotations

import os
import random

import structlog
from groq import Groq

log = structlog.get_logger()

_SYSTEM = """\
You are a financial analyst. Given a passage about a stock, generate one question
that can be answered from the passage and provide the answer.

Return JSON: {"question": "...", "answer": "..."}
Return ONLY the JSON."""


def generate_qa_pair(chunk_text: str, ticker: str) -> dict | None:
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        resp = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant"),
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"Ticker: {ticker}\n\nPassage:\n{chunk_text[:800]}"},
            ],
            max_tokens=200,
            temperature=0.3,
        )
        import json
        raw = resp.choices[0].message.content or "{}"
        start, end = raw.find("{"), raw.rfind("}") + 1
        pair = json.loads(raw[start:end]) if start >= 0 else {}
        if pair.get("question") and pair.get("answer"):
            return {
                "question": pair["question"],
                "answer": pair["answer"],
                "contexts": [chunk_text],
                "ground_truth": pair["answer"],
            }
    except Exception as exc:
        log.warning("synthetic_qa_failed", ticker=ticker, error=str(exc))
    return None


def generate_synthetic_dataset(
    tickers: list[str],
    collection_key: str = "news",
    n_per_ticker: int = 5,
) -> list[dict]:
    """Pull chunks from Qdrant + generate synthetic QA pairs via Groq."""
    from backend.rag.ingestion.collections import collection_name, get_client

    client = get_client()
    col = collection_name(collection_key)
    pairs: list[dict] = []

    for ticker in tickers:
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue
            results, _ = client.scroll(
                collection_name=col,
                scroll_filter=Filter(
                    must=[FieldCondition(key="ticker", match=MatchValue(value=ticker))]
                ),
                limit=n_per_ticker * 3,
                with_payload=True,
            )
            chunks = [r.payload.get("text", "") for r in results if r.payload]
            random.shuffle(chunks)
            for chunk in chunks[:n_per_ticker]:
                if not chunk:
                    continue
                pair = generate_qa_pair(chunk, ticker)
                if pair:
                    pairs.append(pair)
        except Exception as exc:
            log.error("synthetic_ticker_failed", ticker=ticker, error=str(exc))

    log.info("synthetic_dataset_done", total=len(pairs))
    return pairs
