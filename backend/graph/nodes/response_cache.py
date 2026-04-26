"""Shared response cache — imported by response_node and chat route for early bypass."""
from __future__ import annotations

import hashlib
import os
import time

_RESPONSE_CACHE: dict[str, tuple[str, float | None, float]] = {}
_CACHE_TTL = float(os.getenv("RESPONSE_CACHE_TTL", "300"))
_CACHE_PRICE_THRESHOLD = float(os.getenv("RESPONSE_CACHE_PRICE_THRESHOLD", "2.0"))

_VOLATILE_TERMS = frozenset({
    "right now", "just now", "breaking", "latest news", "happening now",
    "this second", "live", "real time", "realtime", "right this moment",
})


def cache_key(ticker: str, query: str, user_mode: str) -> str:
    fingerprint = hashlib.sha256(query.lower().strip().encode()).hexdigest()[:12]
    return f"{ticker}:{fingerprint}:{user_mode}"


def is_volatile_query(query: str) -> bool:
    q = query.lower()
    return any(term in q for term in _VOLATILE_TERMS)


def get_cached(key: str, current_pct: float | None = None) -> str | None:
    """Return cached response if valid. current_pct=None skips price-based invalidation."""
    entry = _RESPONSE_CACHE.get(key)
    if not entry:
        return None
    text, cached_pct, ts = entry
    if (time.monotonic() - ts) > _CACHE_TTL:
        del _RESPONSE_CACHE[key]
        return None
    if current_pct is not None and cached_pct is not None:
        if abs(current_pct - cached_pct) >= _CACHE_PRICE_THRESHOLD:
            del _RESPONSE_CACHE[key]
            return None
    return text


def set_cached(key: str, text: str, pct: float | None) -> None:
    _RESPONSE_CACHE[key] = (text, pct, time.monotonic())
