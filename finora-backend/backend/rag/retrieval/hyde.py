"""
HyDE — Hypothetical Document Embeddings.
Applied to HISTORICAL and NEWS intents with abstract queries.
Skipped for REAL_TIME.
"""
from __future__ import annotations

import os

import structlog
from groq import Groq

from backend.rag.embedder import embed

log = structlog.get_logger()

_HYDE_MODEL = os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant")

_HYDE_PROMPT = """\
Generate a 2-sentence financial analyst note that would directly answer: "{query}"
Be specific: include data points, dates, percentages if possible.
Do not say "I don't know." Write as if you have access to market data."""


def _get_groq() -> Groq:
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_hyde_embedding(query: str) -> list[float]:
    """
    Generate a hypothetical document for the query, then embed it.
    Falls back to embedding the raw query on any failure.
    """
    try:
        client = _get_groq()
        resp = client.chat.completions.create(
            model=_HYDE_MODEL,
            messages=[{"role": "user", "content": _HYDE_PROMPT.format(query=query)}],
            max_tokens=150,
            temperature=0.3,
        )
        hyde_doc = resp.choices[0].message.content or query
        log.debug("hyde_generated", query_len=len(query), doc_len=len(hyde_doc))
        return embed(hyde_doc)
    except Exception as exc:
        log.warning("hyde_failed_fallback_to_query", error=str(exc))
        return embed(query)


def should_use_hyde(intent: str) -> bool:
    """HyDE applies to historical and news intents, not real-time."""
    return intent in {"historical", "news", "fundamental", "comparative"}
