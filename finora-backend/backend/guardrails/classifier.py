"""
Input guardrail — llama-3.1-8b-instant classifies query safety (~150ms).
First node in the LangGraph — blocks unsafe queries before any retrieval.
"""
from __future__ import annotations

import json
import os

import structlog
from groq import Groq

from backend.graph.state import FiNoraState
from backend.guardrails.disclaimers import get_disclaimer

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
You are a financial query safety classifier for an AI financial intelligence platform.

BLOCKED intents — ONLY queries asking for personal-specific investment decisions with personal context, or illegal advice:
- direct_buy_sell_recommendation: queries that combine a personal position with a decision request — "I hold X shares, should I sell?", "I'm thinking of putting my savings into X, should I?", "Should I exit my position now?". NOTE: general questions like "Should I invest in X?", "Is X a good investment?", "Is it worth buying X?" are NOT blocked — they are fundamental_analysis.
- specific_options_strategy: "Buy the $180 call", "What strike to sell?", "Roll my puts", "Which option to buy?"
- insider_trading_context: "Before the announcement...", "I heard from someone at the company", "pre-IPO leak"
- market_manipulation: "How to move the price", "pump and dump", "short squeeze tactics", "coordinate buying"
- personal_financial_planning: "How much of my savings should I put in X?", "I have $50K to invest", "what percentage of my portfolio should be X?"
- tax_evasion_advice: "How to avoid capital gains", "hide gains offshore", "not report profits"

ALLOWED intents — analysis, education, market information:
- fundamental_analysis: PE, EPS, revenue, margins, debt, valuation, "is X expensive?", "what's the fair value?", "should I invest in X?", "is X a good investment?", "is X worth buying?", "is X a good long-term investment?"
- technical_analysis: RSI, MACD, support, resistance, moving averages, chart patterns, momentum
- news_analysis: recent news, earnings results, press releases, catalysts, "why did X move?"
- historical_pattern: past price behavior, earnings history, historical comparisons
- sector_comparison: peers, sector performance, "how does X compare to competitors?"
- market_overview: index levels, macro factors, market conditions
- screener: find stocks matching criteria
- educational: "what does PE mean?", "how does a stock split work?"

NUANCES — these are ALLOWED, not blocked:
- "Should I invest in X?" → fundamental_analysis (investment analysis, NOT personal advice)
- "Is X a good investment?" → fundamental_analysis
- "Is X worth buying now?" → fundamental_analysis
- "Should I buy X?" (without personal context) → fundamental_analysis
- "Is X a good long-term investment?" → fundamental_analysis
- "Is X expensive at current valuation?" → fundamental_analysis (valuation analysis, not buy advice)
- "What's the analyst consensus on X?" → fundamental_analysis
- "What are the risks of investing in X?" → fundamental_analysis (risk education)
- "What do analysts think about X?" → fundamental_analysis
- "Is this a good entry point technically?" → technical_analysis (chart analysis, not personal advice)
- "What's the downside risk for X?" → fundamental_analysis

Return ONLY valid JSON: {"intent": "<intent>", "blocked": true/false}"""

_REDIRECT_MSGS: dict[str, str] = {
    "direct_buy_sell_recommendation": (
        "I can't tell you whether to buy or sell {ticker}, but I can show you what analysts currently "
        "recommend and the valuation picture driving that view. Want the consensus breakdown?"
    ),
    "personal_financial_planning": (
        "Allocation decisions depend on your full financial picture — a registered financial advisor "
        "is the right call for that. I can show you how {ticker} has performed historically and what "
        "analysts currently think about it."
    ),
    "specific_options_strategy": (
        "I can't advise on specific options strategies. I can pull the underlying fundamentals, "
        "recent volatility context, and analyst targets for {ticker} if that's useful."
    ),
    "insider_trading_context": (
        "I can only work with publicly available information. I can surface the latest news, "
        "analyst views, and disclosed filings for {ticker}."
    ),
    "market_manipulation": (
        "That's outside what I can help with. I focus on public market analysis — "
        "price action, fundamentals, and analyst views."
    ),
    "tax_evasion_advice": (
        "I can't advise on tax strategies — consult a certified tax professional for that. "
        "I'm happy to pull the market analysis and fundamentals for {ticker}."
    ),
}
_REDIRECT_DEFAULT = (
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
        redirect = _REDIRECT_MSGS.get(intent, _REDIRECT_DEFAULT).format(ticker=ticker)
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
