"""
Intent → retrieval branch mapping.
Maps each intent to: which collection, whether to use HyDE, retrieval config.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Intent = Literal["real_time", "news", "historical", "fundamental", "comparative", "screener"]


@dataclass
class RetrievalBranch:
    intent: Intent
    collection: str          # Qdrant collection key: 'news' | 'historical' | 'filings'
    use_hyde: bool
    description: str
    allow_global_fallback: bool = False  # historical OK; news must NOT return unrelated articles


_BRANCH_MAP: dict[str, RetrievalBranch] = {
    "news": RetrievalBranch(
        intent="news",
        collection="news",
        use_hyde=True,
        description="News articles, analyst reports, press releases",
        allow_global_fallback=False,
    ),
    "historical": RetrievalBranch(
        intent="historical",
        collection="historical",
        use_hyde=True,
        description="20yr OHLCV event patterns, earnings history, technicals",
        allow_global_fallback=True,
    ),
    "fundamental": RetrievalBranch(
        intent="fundamental",
        collection="filings",
        use_hyde=False,
        description="SEC 10-K/10-Q filings, earnings transcripts",
        allow_global_fallback=False,
    ),
    "comparative": RetrievalBranch(
        intent="comparative",
        collection="news",
        use_hyde=True,
        description="Cross-ticker or cross-sector comparison",
        allow_global_fallback=False,
    ),
}

# Intents that skip RAG entirely (handled by live data nodes)
LIVE_ONLY_INTENTS = {"real_time", "screener"}


def get_branches(intents: list[Intent]) -> list[RetrievalBranch]:
    """Return RAG branches for a set of intents, deduplicating collections."""
    seen_collections: set[str] = set()
    branches: list[RetrievalBranch] = []
    for intent in intents:
        if intent in LIVE_ONLY_INTENTS:
            continue
        branch = _BRANCH_MAP.get(intent)
        if branch and branch.collection not in seen_collections:
            branches.append(branch)
            seen_collections.add(branch.collection)
    return branches
