from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict


Intent = Literal["real_time", "news", "historical", "fundamental", "comparative", "screener"]
UserMode = Literal["insight", "trader"]


class FiNoraState(TypedDict):
    # Input
    query: str
    ticker: str        # display ticker (e.g. "TCS", "RELIANCE")
    yf_ticker: str     # Yahoo Finance ticker (e.g. "TCS.NS", "RELIANCE.NS")
    company_name: str  # full company name (e.g. "Infosys Limited")
    currency: str      # ISO currency code (e.g. "INR", "USD")
    user_mode: UserMode  # "insight" (default) or "trader"
    session_id: str
    conversation_history: list[dict]

    # Routing
    intents: list[Intent]
    guardrail_flags: list[str]
    guardrail_blocked: bool

    # Retrieval outputs (parallel branches append — operator.add merges lists)
    realtime_context: dict | None
    news_chunks: Annotated[list[dict], operator.add]
    filings_chunks: list[dict]
    historical_chunks: Annotated[list[dict], operator.add]
    fundamental_data: dict | None
    sector_context: dict | None  # sector ETF performance + similar stocks

    # Generation
    fused_context: str
    response: str
    citations: list[dict]
    confidence_score: float
    disclaimer_text: str

    # Observability
    trace_id: str
    retrieval_scores: dict
