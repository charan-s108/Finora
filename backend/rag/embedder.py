import os
from functools import lru_cache

import numpy as np


@lru_cache(maxsize=1)
def get_embedder():
    from sentence_transformers import SentenceTransformer
    model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    return SentenceTransformer(model)


def embed(text: str) -> list[float]:
    return get_embedder().encode(text, normalize_embeddings=True).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    return get_embedder().encode(texts, normalize_embeddings=True, batch_size=32).tolist()


VECTOR_SIZE = 384
