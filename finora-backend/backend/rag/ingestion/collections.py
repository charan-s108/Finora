import os

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, OptimizersConfigDiff, PayloadSchemaType

from backend.rag.embedder import VECTOR_SIZE

log = structlog.get_logger()

COLLECTIONS = {
    "finora_news": "QDRANT_COLLECTION_NEWS",
    "finora_historical": "QDRANT_COLLECTION_HISTORICAL",
    "finora_filings": "QDRANT_COLLECTION_FILINGS",
}


def get_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    if not url:
        raise RuntimeError("QDRANT_URL not set")
    return QdrantClient(url=url, api_key=api_key, timeout=30)


def ensure_collections(client: QdrantClient | None = None) -> None:
    """Create all three collections if they don't exist."""
    c = client or get_client()
    existing = {col.name for col in c.get_collections().collections}

    for default_name, env_key in COLLECTIONS.items():
        name = os.getenv(env_key, default_name)
        if name in existing:
            log.info("collection_exists", name=name)
            continue
        c.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            optimizers_config=OptimizersConfigDiff(indexing_threshold=20_000),
        )
        # Payload index required for ticker-filtered searches
        c.create_payload_index(
            collection_name=name,
            field_name="ticker",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        log.info("collection_created", name=name)


def collection_name(key: str) -> str:
    """key: 'news' | 'historical' | 'filings'"""
    env_map = {
        "news": "QDRANT_COLLECTION_NEWS",
        "historical": "QDRANT_COLLECTION_HISTORICAL",
        "filings": "QDRANT_COLLECTION_FILINGS",
    }
    return os.getenv(env_map[key], f"finora_{key}")
