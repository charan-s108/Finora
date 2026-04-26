"""
Ingest news articles via NewsAPI → SlidingWindowChunker → Qdrant (finora_news).
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import requests
import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from rag.chunking.strategies import SlidingWindowChunker
from rag.embedder import embed_batch
from rag.ingestion.collections import collection_name, get_client

log = structlog.get_logger()

_chunker = SlidingWindowChunker(window=512, stride=128)

_NEWSAPI_BASE = "https://newsapi.org/v2/everything"
_RSS_SOURCES = [
    "reuters.com",
    "bloomberg.com",
    "ft.com",
    "wsj.com",
    "cnbc.com",
    "businessinsider.com",
]


def _fetch_newsapi(ticker: str, company_name: str, days: int = 7) -> list[dict]:
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        log.warning("newsapi_key_missing")
        return []

    from_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    query = f'"{company_name}" OR "{ticker}"'

    try:
        resp = requests.get(
            _NEWSAPI_BASE,
            params={
                "q": query,
                "from": from_date,
                "sortBy": "relevancy",
                "language": "en",
                "pageSize": 20,
                "domains": ",".join(_RSS_SOURCES),
                "apiKey": api_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("articles", [])
    except Exception as exc:
        log.error("newsapi_fetch_failed", ticker=ticker, error=str(exc))
        return []


def _article_to_text(article: dict) -> str:
    parts = []
    if article.get("title"):
        parts.append(article["title"])
    if article.get("description"):
        parts.append(article["description"])
    if article.get("content"):
        # NewsAPI free tier truncates at ~200 chars; use what we have
        content = article["content"].replace("[+", "").split("[+")[0].strip()
        if content:
            parts.append(content)
    return " ".join(parts)


def ingest_ticker(
    ticker: str,
    company_name: str,
    days: int = 7,
    client: QdrantClient | None = None,
) -> int:
    c = client or get_client()
    col = collection_name("news")

    articles = _fetch_newsapi(ticker, company_name, days)
    if not articles:
        log.warning("news_no_articles", ticker=ticker)
        return 0

    all_chunks = []
    for article in articles:
        text = _article_to_text(article)
        if len(text) < 100:
            continue

        published_at = article.get("publishedAt", "")
        source = article.get("source", {}).get("name", "unknown")
        url = article.get("url", "")

        meta = {
            "ticker": ticker,
            "source": source,
            "url": url,
            "published_at": published_at,
            "title": article.get("title", ""),
        }
        chunks = _chunker.chunk(text, metadata=meta)
        all_chunks.extend(chunks)

    if not all_chunks:
        return 0

    texts = [ch.text for ch in all_chunks]
    vectors = embed_batch(texts)

    points = [
        PointStruct(
            id=str(uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"{ticker}:{ch.metadata.get('url','')}:{ch.metadata.get('chunk_start_token', i)}",
            )),
            vector=vec,
            payload={**ch.metadata, "text": ch.text, "data_type": "news"},
        )
        for i, (ch, vec) in enumerate(zip(all_chunks, vectors))
    ]

    c.upsert(collection_name=col, points=points)
    log.info("news_ingest_done", ticker=ticker, articles=len(articles), chunks=len(points))
    return len(points)


def ingest_universe(stocks: list[dict], days: int = 7) -> dict[str, int]:
    client = get_client()
    results: dict[str, int] = {}

    for stock in stocks:
        ticker = stock["ticker"]
        name = stock.get("name", ticker)
        try:
            results[ticker] = ingest_ticker(ticker, name, days=days, client=client)
        except Exception as exc:
            log.error("news_worker_failed", ticker=ticker, error=str(exc))
            results[ticker] = 0
        time.sleep(0.5)  # NewsAPI free tier: 100 req/day

    return results
