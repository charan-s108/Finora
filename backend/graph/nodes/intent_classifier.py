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

from graph.state import FiNoraState, Intent

log = structlog.get_logger()

_MODEL = os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant")

_SYSTEM = """\
You are a financial query intent classifier. Classify the user query into one or more intents.

Intents:
- real_time: live price, today's movement, current volume, intraday
- news: recent news, announcements, catalysts, analyst notes, press releases
- historical: past patterns, earnings history, 20yr comparison, technical patterns
- fundamental: PE, EPS, revenue, margins, balance sheet, valuation
- comparative: compare two stocks or sectors
- screener: find stocks matching criteria

Rules:
- Return a JSON array of intents. Example: ["real_time", "news"]
- Always include real_time if the query asks about today's movement
- Multi-intent is normal: "Why did Apple drop today?" → ["real_time", "news", "historical"]
- Return ONLY the JSON array, no explanation."""


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
        intents: list[Intent] = json.loads(raw[start:end]) if start >= 0 else ["real_time", "news"]

        valid = {"real_time", "news", "historical", "fundamental", "comparative", "screener"}
        intents = [i for i in intents if i in valid] or ["real_time", "news"]

    except Exception as exc:
        log.warning("intent_classifier_failed", error=str(exc))
        intents = ["real_time", "news"]

    log.info("intents_classified", query=query[:60], intents=intents, trace_id=trace_id)
    return {"intents": intents, "trace_id": trace_id}
