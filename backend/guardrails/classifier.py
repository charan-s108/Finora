"""
Input guardrail — llama-3.1-8b-instant classifies query safety (~150ms).
First node in the LangGraph — blocks unsafe queries before any retrieval.
"""
from __future__ import annotations

import json
import os

import structlog
from groq import Groq

from graph.state import FiNoraState
from guardrails.disclaimers import get_disclaimer

log = structlog.get_logger()

_MODEL = os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant")

# Always blocked — regardless of user_mode
_ALWAYS_BLOCKED = {
    "insider_trading_context",
    "market_manipulation",
    "tax_evasion_advice",
    "specific_options_strategy",
}

# Blocked in INSIGHT mode only — TRADER mode receives signal-based response instead
_INSIGHT_ONLY_BLOCKED = {
    "direct_buy_sell_recommendation",
    "personal_financial_planning",
}

# Combined set for insight mode
_BLOCKED_INTENTS = _ALWAYS_BLOCKED | _INSIGHT_ONLY_BLOCKED

_SYSTEM = """\
You are a financial query safety classifier.
Classify the query intent as one of:
- allowed: fundamental_analysis, technical_analysis, news_analysis, historical_pattern,
           sector_comparison, earnings_analysis, market_overview, screener, educational
- blocked: direct_buy_sell_recommendation, specific_options_strategy, insider_trading_context,
           market_manipulation, personal_financial_planning, tax_evasion_advice

Return JSON: {"intent": "<intent>", "blocked": true/false}
Return ONLY the JSON."""

_REDIRECT_MSG = (
    "I can't make specific investment recommendations, but I can pull what analysts "
    "currently say about {ticker} and the key metrics to consider. "
    "Want me to surface the consensus view and recent developments?"
)


def guardrail_check_node(state: FiNoraState) -> dict:
    if os.getenv("GUARDRAILS_ENABLED", "true").lower() != "true":
        return {"guardrail_blocked": False, "guardrail_flags": []}

    query = state["query"]
    ticker = state.get("ticker", "the stock")

    user_mode = state.get("user_mode", "insight")
    # In trader mode, buy/sell and personal planning queries are allowed through
    # (response_node handles them with signal-based framing + risk disclosure)
    blocked_set = _ALWAYS_BLOCKED if user_mode == "trader" else _BLOCKED_INTENTS

    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        resp = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"Query: {query}"},
            ],
            max_tokens=60,
            temperature=0.0,
        )
        raw = resp.choices[0].message.content or "{}"
        start, end = raw.find("{"), raw.rfind("}") + 1
        result = json.loads(raw[start:end]) if start >= 0 else {}
        intent = result.get("intent", "allowed")
        blocked = intent in blocked_set
    except Exception as exc:
        log.warning("guardrail_classifier_failed", error=str(exc))
        blocked = False
        intent = "allowed"

    flags = [intent] if blocked else []
    log.info("guardrail_check", query=query[:60], blocked=blocked, intent=intent, user_mode=user_mode)

    if blocked:
        redirect = _REDIRECT_MSG.format(ticker=ticker)
        disclaimer = get_disclaimer(os.getenv("DISCLAIMER_LOCALE", "IN"))
        return {
            "guardrail_blocked": True,
            "guardrail_flags": flags,
            "response": redirect,
            "disclaimer_text": disclaimer,
            "fused_context": "",
            "confidence_score": 0.0,
            "citations": [],
        }

    return {"guardrail_blocked": False, "guardrail_flags": flags}


def route_after_guardrail(state: FiNoraState) -> str:
    return "blocked" if state.get("guardrail_blocked") else "allowed"
