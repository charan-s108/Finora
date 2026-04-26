from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class SlidingWindowChunker:
    """
    Overlapping token-window chunker for news articles and analyst reports.
    window=512 tokens, stride=128 tokens.
    """

    def __init__(self, window: int = 512, stride: int = 128) -> None:
        self.window = window
        self.stride = stride

    def _tokenize(self, text: str) -> list[str]:
        return text.split()

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        meta = metadata or {}
        tokens = self._tokenize(text)
        chunks: list[Chunk] = []

        start = 0
        while start < len(tokens):
            end = min(start + self.window, len(tokens))
            chunk_text = " ".join(tokens[start:end])
            if len(chunk_text.strip()) > 50:
                chunks.append(Chunk(
                    text=chunk_text,
                    metadata={**meta, "chunk_start_token": start, "chunk_end_token": end},
                ))
            if end == len(tokens):
                break
            start += self.stride

        return chunks


class SemanticChunker:
    """
    Boundary-detection chunker for SEC filings and earnings transcripts.
    Splits on cosine similarity drops between adjacent sentence embeddings.
    chunk size: 300-800 tokens (variable, topic-coherent).
    """

    def __init__(self, threshold: float = 0.75, min_tokens: int = 300, max_tokens: int = 800) -> None:
        self.threshold = threshold
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens

    def _split_sentences(self, text: str) -> list[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if len(s.strip()) > 20]

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        from rag.embedder import get_embedder
        import numpy as np

        meta = metadata or {}
        sentences = self._split_sentences(text)
        if not sentences:
            return []

        if len(sentences) <= 3:
            return [Chunk(text=text, metadata=meta)]

        embedder = get_embedder()
        embeddings = embedder.encode(sentences, normalize_embeddings=True, batch_size=32)

        # Detect boundary: cosine similarity drop between adjacent sentences
        boundaries = [0]
        current_tokens = len(sentences[0].split())

        for i in range(1, len(sentences)):
            sim = float(np.dot(embeddings[i - 1], embeddings[i]))
            current_tokens += len(sentences[i].split())

            is_boundary = (
                (sim < self.threshold and current_tokens >= self.min_tokens)
                or current_tokens >= self.max_tokens
            )
            if is_boundary:
                boundaries.append(i)
                current_tokens = 0

        boundaries.append(len(sentences))

        chunks: list[Chunk] = []
        for j in range(len(boundaries) - 1):
            chunk_sentences = sentences[boundaries[j]:boundaries[j + 1]]
            chunk_text = " ".join(chunk_sentences)
            if len(chunk_text.strip()) > 100:
                chunks.append(Chunk(
                    text=chunk_text,
                    metadata={**meta, "chunk_index": j},
                ))

        return chunks


class FixedTokenChunker:
    """Simple fixed-size chunker, no overlap. Fallback for structured data."""

    def __init__(self, size: int = 512) -> None:
        self.size = size

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        meta = metadata or {}
        tokens = text.split()
        chunks: list[Chunk] = []
        for i in range(0, len(tokens), self.size):
            chunk_text = " ".join(tokens[i:i + self.size])
            if chunk_text.strip():
                chunks.append(Chunk(text=chunk_text, metadata={**meta, "chunk_index": i // self.size}))
        return chunks
