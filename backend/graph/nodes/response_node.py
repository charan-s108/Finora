"""Response node — Groq llama-3.3-70b with mode-aware output, response cache, and 8B fallback."""
from __future__ import annotations

import os

import structlog
from groq import Groq

from graph.nodes.response_cache import cache_key, get_cached, is_volatile_query, set_cached
from graph.state import FiNoraState
from guardrails.output_filter import apply_output_guardrail

log = structlog.get_logger()

_GROQ_MODEL_PRIMARY = os.getenv("GROQ_MODEL_PRIMARY", "openai/gpt-oss-120b")
_GROQ_MODEL_FALLBACK = os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant")
_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "1200"))
_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.15"))

_SYSTEM_INSIGHT = """You are Finora AI — a financial intelligence system. Behave like an analyst reading a dashboard, not a chatbot.

STRICT RULES:
- Never hallucinate numbers. Ground every statement in provided data.
- Interpret metrics, don't restate them. High PE = premium valuation — say why it matters.
- Correct currency: INR for Indian stocks, USD for US stocks. Use company name, not ticker.
- No emojis.

OPENING — NON-NEGOTIABLE:
- First sentence states what the stock is doing, grounded in [MARKET CONTEXT].
- Never start with: "Based on", "According to", "The data shows".
- Good: "Apple is down 0.9% today with no strong momentum — markets appear to be waiting ahead of earnings."

RESPONSE POSTURE: Follow [RESPONSE POSTURE] exactly — it controls certainty level.

SIGNAL DIVERGENCE: If [SIGNAL DIVERGENCE] present, name it in one sentence.
- Good: "Price is down 2% but 78% of analysts rate Buy — the market may be discounting near-term noise."

INTENSITY AWARENESS:
- Query uses strong language but data shows mild move → use contrast phrases: "no signs of heavy selling", "price action remains orderly", "no panic-driven volume"
- Data confirms sharp move → match intensity, be direct.
- Never reference the user's wording. Let data speak.

BANNED WORDS: suggesting, indicating, implying, appears to, seems to, would suggest, dominant signal, uncertainty flag, MARKET CONTEXT, RESPONSE POSTURE, SIGNAL DIVERGENCE, "not X% as stated", "discrepancy", "does not match", "despite the", "as you mentioned", mixed signals, it depends

HISTORICAL PATTERNS: If [HISTORICAL PATTERNS] present → reference at least one. Integrate naturally: "This mirrors [date] when the stock [outcome]."

STYLE: 1-2 tight sentences per section. Each section adds new info. Expand where data is strong; omit where weak.
- [UNAVAILABLE] / [NO DATA] / [LIMITED] → skip that section entirely, no explanation.
- Low signal fallback: "No strong directional signal is present — the stock is consolidating."

OUTPUT — summary queries:
## What's Happening
## Fundamentals
## Technical Trend
## Analyst Sentiment
## Recent Drivers
## Key Risks

OUTPUT — focused queries: Answer directly. No headers. Max 100 words.

For buy/sell queries: price action + analyst sentiment + top risk, then end with EXACTLY:
Consider consulting a financial advisor before making investment decisions."""

_SYSTEM_TRADER = """You are Finora AI — financial intelligence for active traders. Behave like a quant analyst at a trading desk — data-first, directional, precise.

STRICT RULES:
- Never hallucinate numbers. Ground every statement in provided data.
- Be specific and directional. Correct currency: INR Indian, USD US. Company name, not ticker.
- No emojis.

OPENING — NON-NEGOTIABLE:
- First sentence: stock action + explicit directional bias (bullish / bearish / neutral).
- Never start with: "Based on", "According to", "The data shows".
- Good: "Momentum is neutral — Apple is down 0.9% on below-average volume, consolidating ahead of earnings."

RESPONSE POSTURE: Follow [RESPONSE POSTURE] exactly — controls certainty and directional strength.

SIGNAL DIVERGENCE: If [SIGNAL DIVERGENCE] present, name it — most actionable signal for a trader.
- Good: "Price is down 2.4% but 78% of analysts rate Buy — this divergence may signal opportunity or analyst lag."

INTENSITY AWARENESS:
- Query uses strong language but data shows mild move → contrast phrases: "no signs of heavy selling", "price action remains orderly", "no panic-driven volume"
- Data confirms sharp move → match intensity, be urgent.
- Never reference the user's wording.

BANNED WORDS: suggesting, indicating, implying, appears to, seems to, would suggest, dominant signal, uncertainty flag, MARKET CONTEXT, RESPONSE POSTURE, SIGNAL DIVERGENCE, "not X% as stated", "discrepancy", "does not match", "despite the", "as you mentioned"

HISTORICAL PATTERNS: If [HISTORICAL PATTERNS] present → reference at least one. "This setup mirrors [event] in [date] when the stock [return outcome]."

STYLE: 1-2 tight sentences per section. Each section adds new info. Expand where data is strong.
- [UNAVAILABLE] / [NO DATA] / [LIMITED] → skip that section entirely.
- Low signal fallback: "No strong directional signal. Momentum is neutral — exercise caution."

OUTPUT — summary queries:
## What's Happening
## Fundamentals
## Technical Trend
## Analyst Sentiment
## Recent Drivers
## Key Risks
## Signals That Matter (always include for trader mode)

OUTPUT — focused queries: Answer directly. No headers. Max 150 words. Always state directional bias.

For buy/sell queries: current signals + key risk, end with:
This is market intelligence, not financial advice — trading decisions rest with you.
NEVER give absolute directives ("you should buy", "go long now")."""


def _cache_key(ticker: str, query: str, user_mode: str) -> str:
    fingerprint = hashlib.sha256(query.lower().strip().encode()).hexdigest()[:12]
    return f"{ticker}:{fingerprint}:{user_mode}"


def _call_groq(client: Groq, model: str, system_prompt: str, fused_context: str) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": fused_context},
        ],
        max_tokens=_MAX_TOKENS,
        temperature=_TEMPERATURE,
    )
    return resp.choices[0].message.content or ""


def response_node(state: FiNoraState) -> dict:
    fused_context = state.get("fused_context", "")
    confidence = state.get("confidence_score", 0.0)
    disclaimer = state.get("disclaimer_text", "")
    locale = os.getenv("DISCLAIMER_LOCALE", "IN")
    user_mode = state.get("user_mode", "insight")
    ticker = state.get("ticker", "")
    query = state.get("query", "")
    current_pct = (state.get("realtime_context") or {}).get("pct_change")

    if not fused_context:
        return {"response": "I don't have enough data to answer that query."}

    system_prompt = _SYSTEM_TRADER if user_mode == "trader" else _SYSTEM_INSIGHT

    # Cache lookup — skip for volatile/live queries
    cache_hit = False
    text = ""
    if ticker and query and not is_volatile_query(query):
        key = cache_key(ticker, query, user_mode)
        cached = get_cached(key, current_pct)
        if cached:
            log.info("response_cache_hit", ticker=ticker, user_mode=user_mode)
            text = cached
            cache_hit = True

    if not cache_hit:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        model_used = _GROQ_MODEL_PRIMARY
        try:
            text = _call_groq(client, _GROQ_MODEL_PRIMARY, system_prompt, fused_context)
        except Exception as exc:
            err_str = str(exc)
            # 429 rate limit → fall back to 8B (separate TPD bucket on Groq free tier)
            if "429" in err_str or "rate_limit" in err_str.lower():
                log.warning("groq_primary_rate_limited_falling_back_to_8b", error=err_str[:120])
                try:
                    text = _call_groq(client, _GROQ_MODEL_FALLBACK, system_prompt, fused_context)
                    model_used = _GROQ_MODEL_FALLBACK
                except Exception as fallback_exc:
                    log.error("groq_fallback_also_failed", error=str(fallback_exc))
                    text = "I encountered an error generating the analysis. Please try again."
            else:
                log.error("groq_generation_failed", error=err_str)
                text = "I encountered an error generating the analysis. Please try again."

        # Cache successful primary-model responses only
        if text and model_used == _GROQ_MODEL_PRIMARY and ticker and query and not is_volatile_query(query):
            set_cached(cache_key(ticker, query, user_mode), text, current_pct)

    text = apply_output_guardrail(
        response=text,
        fused_context=fused_context,
        confidence_score=confidence,
        disclaimer_text=disclaimer,
        locale=locale,
    )

    log.info(
        "response_ok",
        chars=len(text),
        confidence=confidence,
        cache_hit=cache_hit,
        user_mode=user_mode,
    )
    return {"response": text}
