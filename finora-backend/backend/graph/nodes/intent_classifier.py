"""
Intent classification node — llama-3.1-8b-instant (~200ms).
Classifies query into one or more intents that drive graph fan-out.
"""
from __future__ import annotations

import json
import os
import uuid

import structlog
from groq import Groq

from backend.graph.state import FiNoraState, Intent

log = structlog.get_logger()

_MODEL = os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant")

_SYSTEM = """\
You are a financial query intent classifier. Classify the user query into one or more intents.

Intents:
- real_time: live price, today's movement, current volume, intraday
- news: recent news, announcements, catalysts, analyst notes, press releases
- historical: past patterns, earnings history, 20yr comparison, technical patterns
- fundamental: PE, EPS, revenue, margins, balance sheet, valuation
- comparative: compare two stocks or sectors, sector performance, peers, similar stocks, competitors
- screener: find stocks matching criteria

INCLUDE news for: "why", "what's driving", "catalyst", "reason", "what happened", "latest", "moving", "dropped", "surged", "crashed", "rally", explicit news requests
DO NOT include news for: pure fundamental queries (PE, EPS, revenue, valuation, margins), pure technical queries (RSI, MACD, support, resistance, moving average), basic price or volume lookups
INCLUDE comparative for: "sector", "peers", "similar stocks", "competitors", "how does it compare", "vs", "against", "sector performance", "industry peers", "sector heatmap"

Examples:
- "Why did Apple drop today?" → ["real_time", "news", "historical"]
- "What is the PE ratio?" → ["fundamental"]
- "What's the RSI?" → ["real_time", "historical"]
- "Latest news on NVDA" → ["news"]
- "What's AAPL trading at?" → ["real_time"]
- "Compare AAPL and MSFT earnings" → ["fundamental", "historical", "comparative"]
- "How is the tech sector doing?" → ["real_time", "comparative"]
- "Show me similar stocks to AAPL" → ["comparative"]
- "Who are Apple's peers?" → ["comparative"]
- "How does AAPL compare to its sector?" → ["real_time", "fundamental", "comparative"]

Return ONLY the JSON array, no explanation."""


_SUMMARY_TRIGGERS = {
    "summarize", "summary", "explain", "overview", "what's happening",
    "whats happening", "tell me about", "breakdown", "analyse", "analyze",
    "give me a", "what do you think", "how is", "how's",
}

_ALL_INTENTS: list[Intent] = ["real_time", "fundamental", "news", "historical"]


def _is_summary_query(query: str) -> bool:
    q = query.lower().strip()
    return any(trigger in q for trigger in _SUMMARY_TRIGGERS)


def intent_classifier_node(state: FiNoraState) -> dict:
    query = state["query"]
    ticker = state.get("ticker", "")
    trace_id = state.get("trace_id") or str(uuid.uuid4())[:8]

    # Summary queries always fire all 4 branches — need full data for narrative
    if _is_summary_query(query):
        log.info("intents_classified", query=query[:60], intents=_ALL_INTENTS,
                 trace_id=trace_id, reason="summary_shortcut")
        return {"intents": _ALL_INTENTS, "trace_id": trace_id}

    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        prompt = f'Ticker context: {ticker}\nQuery: "{query}"'

        resp = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=60,
            temperature=0.0,
        )
        raw = resp.choices[0].message.content or "[]"

        start = raw.find("[")
        end = raw.rfind("]") + 1
        intents = json.loads(raw[start:end]) if start >= 0 else ["real_time"]

        valid = {"real_time", "news", "historical", "fundamental", "comparative", "screener"}
        intents = [i for i in intents if i in valid] or ["real_time"]

    except Exception as exc:
        log.warning("intent_classifier_failed", error=str(exc))
        intents = ["real_time"]

    log.info("intents_classified", query=query[:60], intents=intents, trace_id=trace_id)
    return {"intents": intents, "trace_id": trace_id}
