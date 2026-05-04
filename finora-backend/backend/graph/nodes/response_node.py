"""Response node — intent-routed system prompts, per-intent token limits, Groq with 8B fallback."""
from __future__ import annotations

import os
import re

import structlog
from groq import Groq

from backend.graph.nodes.response_cache import cache_key, get_cached, is_volatile_query, set_cached
from backend.graph.state import FiNoraState
from backend.guardrails.output_filter import apply_output_guardrail

log = structlog.get_logger()

_GROQ_MODEL_PRIMARY = os.getenv("GROQ_MODEL_PRIMARY", "openai/gpt-oss-120b")
_GROQ_MODEL_FALLBACK = os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant")
_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.15"))

# ─────────────────────────────────────────────────────────────────────────────
# Shared safety + formatting baseline — injected into every composed prompt
# ─────────────────────────────────────────────────────────────────────────────

_BASE_GUARDRAILS = """GLOBAL RULES (apply to every response — non-negotiable):
- Use ONLY data from the provided context. Never invent numbers or events.
- MISSING DATA: For metric queries → explicitly say "The exact value isn't available in the current data." For all other queries → skip missing data silently, no mention.
- Every statement must follow CAUSE → EFFECT: what happened → why it matters for the investor/trader.
- ANTI-GENERIC: If a sentence can apply to Microsoft, Amazon, or any other company without change, it is invalid — rewrite it using this company's specific data, product, or event.
- No repetition — each sentence must add new information. Never restate the same insight in different words.
- Avoid repeating the same sentence structure across sections — vary phrasing naturally like a human explaining to a friend, not a document being filed.
- Do NOT add sections, headers, or structure beyond what the intent requires.
- NEVER start with: "Based on", "According to", "The data shows", "I".
- BANNED WORDS: suggesting, indicating, implying, appears to, seems to, would suggest, mixed signals, discrepancy, uncertainty flag.
- All section headers use `##` only — never `###`. Headers must always start on a new line with a blank line before them.
- INR for Indian stocks, USD for US stocks. Company name, never ticker symbol.
- UNITS MANDATORY: Every financial value must carry its unit. Revenue/FCF/debt → $B or ₹Cr. Percentages → %. Ratios → x. Never write a bare number — write "$99B", "29x P/E", "3.2%" not just "99", "29", "3.2".
- CONFIDENCE SHAPING: If data is limited or signals conflict, reduce certainty — use "leans bullish" instead of "bullish", "cautiously bearish" instead of "bearish".
- Insight mode: plain English, assume zero finance background, meaning over numbers.
- Trader mode: concise, data-driven, every sentence defends a directional stance."""

# ─────────────────────────────────────────────────────────────────────────────
# Mode base blocks — reasoning + stance rules, mode-specific voice
# ─────────────────────────────────────────────────────────────────────────────

_MODE_BASE_INSIGHT = """REASONING (apply before writing anything):
- You are making a FINANCIAL ARGUMENT for a non-financial reader. Defend a stance — do not summarize data.
- Identify ONE dominant driver (e.g., earnings acceleration, valuation risk). Every section connects back to it. Remove anything that does not support the thesis.
- First sentence must express a VIEW, not describe an event.
  WRONG: "Stock rose 3.3% after earnings beat."
  RIGHT: "Bullish — earnings acceleration removes the bear case and justifies the premium valuation."
- Commit to ONE stance: Bullish, Bearish, or Neutral. Never "mixed" or "unclear".
- When the user presents a conflicting scenario: assume it is valid, name both signals, state which dominates, explain why (timeframe or structural impact).
- [MARKET CONTEXT] from the data is your directional anchor — your opening must flow from it.
- [SIGNAL DIVERGENCE] when present: name the dominant signal explicitly.
- Use only the minimum numbers required to support the argument (typically 1–3 per section). Replace raw metrics with plain-English meaning wherever possible:
  WRONG: "Revenue grew 6% YoY to $416.2B"
  RIGHT: "Sales are growing again after two flat years — the business is re-accelerating"
- Priority order: earnings/growth momentum > valuation > analyst sentiment > noise.

DATA LAYERS — use each layer for its designated purpose (skip silently if absent or marked [NO ... DATA]):
- [NEWS] + [FILINGS CONTEXT]: Catalysts, earnings results, management commentary, events, recent headlines
- [HISTORICAL PATTERN]: Past similar setups — cite the period (e.g. "2022 earnings week") and forward return
- [ANNUAL INCOME HISTORY]: Multi-year revenue and net income trends — use for Revenue & Profit section
- [ANNUAL CASH FLOW HISTORY]: Multi-year FCF, operating cash flow — use for Cash Flow section
- [ANNUAL BALANCE SHEET HISTORY]: Multi-year debt, cash, equity — use for Balance Sheet section
- [FINANCIAL STATEMENTS]: Detailed statement data when ANNUAL HISTORY is insufficient
- [FUNDAMENTALS]: PE, Forward PE, EPS, margins, analyst consensus — use for Valuation and Analyst sections
- [REAL-TIME DATA]: Today's price, volume, 52-week range — use for Price Action and as supporting signal
- [INSIGHT FLAGS]: Pre-computed interpretations — use as directional support, not raw output"""

_MODE_BASE_TRADER = """REASONING (apply before writing anything):
- You are building a TRADE ARGUMENT. Every sentence defends a directional stance.
- Identify ONE dominant trade driver. Every section supports it. Strip anything irrelevant to the trade.
- First sentence must express a directional VIEW, not an event description.
  WRONG: "Stock up 3.3% after earnings beat."
  RIGHT: "Bullish — earnings acceleration removes the key bear argument; volume surge confirms institutional conviction."
- Commit to ONE stance: Bullish, Bearish, or Neutral. Never "mixed".
- Each section must answer: "What does this mean for my position RIGHT NOW?"
- When the user presents a conflicting scenario: assume valid, name both signals, state which dominates, give the trade implication.
- [MARKET CONTEXT] is your directional anchor — opening stance must flow from it.
- [SIGNAL DIVERGENCE] when present: name dominant signal, state the trade setup explicitly.
- Priority order: earnings/growth momentum > valuation > analyst sentiment > noise.

DATA LAYERS — use each layer for its designated purpose (skip silently if absent or marked [NO ... DATA]):
- [NEWS] + [FILINGS CONTEXT]: Catalysts, earnings results, management commentary, events, recent headlines
- [HISTORICAL PATTERN]: Past similar setups — cite the period and forward return; use for trade scenario calibration
- [ANNUAL INCOME HISTORY] + [ANNUAL CASH FLOW HISTORY]: Multi-year financial trends — use for Financials section
- [ANNUAL BALANCE SHEET HISTORY]: Debt and liquidity picture — leverage risk for the trade
- [FINANCIAL STATEMENTS]: Detailed data when ANNUAL HISTORY is insufficient
- [FUNDAMENTALS]: PE, Forward PE, EPS, analyst consensus — use for Valuation and Analyst sections
- [REAL-TIME DATA]: Today's price, volume, 52-week range — primary input for Price Action section
- [INSIGHT FLAGS]: Pre-computed signals — use as directional support, cite them by name"""

# ─────────────────────────────────────────────────────────────────────────────
# Intent-specific instruction blocks — compact but complete
# ─────────────────────────────────────────────────────────────────────────────

_FOLLOW_UP_BLOCK = """
After your response, append:
---SUGGESTIONS---
3 short follow-up questions (max 8 words each), one per line. Cover 3 different angles. No numbers, tickers, bullets, or prices — plain question text only."""

_INTENT_METRIC = """METRIC QUERY — answer one specific financial data point.
- 1–3 sentences only. No headers, no bullets, no structure.
- You MUST include the actual numeric value if it exists in the data — a response without the number is invalid.
- Sentence 1: state the value with units ($, %, x, B).
- Sentence 2: explain what the metric means in plain English.
- Sentence 3: interpret it for THIS company's specific growth, risk, or competitive context — not generic finance theory.""" + _FOLLOW_UP_BLOCK

_INTENT_EXPLAIN = """EXPLAIN QUERY — define the concept, then ground it in reality.
- 2–4 sentences. No headers unless the topic has multiple distinct parts.
- Sentence 1: plain-English definition of the concept.
- Sentence 2–3: if THIS company's specific data exists in context, use it with the actual numbers. If not, ALWAYS produce a vivid real-world analogy that makes the concept concrete — never leave sentence 2 blank, never say data is unavailable.
- CAUSE→EFFECT: what does this concept reveal about the company's (or market's) situation?
- Never use financial jargon without immediately defining it.""" + _FOLLOW_UP_BLOCK

_INTENT_TRADE_INSIGHT = """TRADE/INVESTMENT QUERY — investor asking if a stock is worth buying or investing in.
- NEVER refuse or deflect. NEVER say "I can't tell you whether to buy or sell."
- If the query also asks to explain a concept (e.g., "explain P/E and should I buy?"), briefly define the concept first (1 sentence), then give the trade stance.
- Give a clear directional stance: Bullish / Bearish / Neutral.
- Structure: [optional concept definition] → Stance → ONE strongest supporting signal (with actual data) → ONE biggest risk (with actual data) → timeframe tag.
- No full summary structure, no headers.
- End EXACTLY with this line: Consider consulting a financial advisor before making investment decisions.""" + _FOLLOW_UP_BLOCK

_INTENT_TRADE_TRADER = """TRADE/INVESTMENT QUERY — trader asking for a directional trade read.
- NEVER deflect. Commit to Bullish / Bearish / Neutral in the very first sentence.
- If the query also asks to explain a concept, define it in one sentence first, then give the trade stance.
- Structure: [optional concept definition] → Stance → strongest signal (with data) → biggest risk (with data) → short/long-term timeframe.
- If a price level, trigger, or key technical level is derivable from data, include it.
- No full summary structure.
- End with: This is market intelligence, not financial advice — trading decisions rest with you.""" + _FOLLOW_UP_BLOCK

_INTENT_SUMMARIZE_INSIGHT = """SUMMARY QUERY — full structured analysis for an everyday investor.
Produce ALL sections where data exists. `##` headers only — NEVER `###`.

## [Company Name] — [Bullish/Bearish/Neutral]: [ONE-LINE ARGUMENT — the dominant driver and why it matters]
Example: ## Apple — Bullish: earnings re-acceleration removes the bear case, buyback floors the stock

## The Business
One sentence: what the company does and how it earns money — specific to this company.
(draw from [FILINGS CONTEXT] and [FUNDAMENTALS])

## Revenue & Profit
2–3 most recent fiscal years. Focus on the TREND and what it means — not the raw numbers.
Max 2 numbers. Replace metrics with meaning.
(draw from [ANNUAL INCOME HISTORY])

## Cash Flow
Most recent year. Is the core business a cash machine or cash burner — and what does that enable?
(draw from [ANNUAL CASH FLOW HISTORY])

## Balance Sheet
Most recent year. Cash-rich or debt-heavy — what does that mean for the investor's risk?
(draw from [ANNUAL BALANCE SHEET HISTORY])

## Valuation
Is the stock cheap, fair, or expensive given what the company actually earns? One key metric + analyst target.
(draw from [FUNDAMENTALS])

## What Analysts Think
Buy/Hold/Sell split. Is the analyst community broadly confident or cautiously split?
(draw from [FUNDAMENTALS] analyst consensus block)

## Recent Drivers
2–3 specific events — each anchored to an actual headline and its stock implication.
(draw from [NEWS] and [FILINGS CONTEXT])

## Historical Parallels
If [HISTORICAL PATTERN] data exists → MUST include this section: cite the period and forward return, state what it implies now.
If [HISTORICAL PATTERN] is absent or marked [NO HISTORICAL PATTERN DATA] → skip silently.
(draw from [HISTORICAL PATTERN])

## Key Risks
2–3 risks using `- ` bullet format (NOT numbered), each tied to a real data point, each ending with a timeframe tag: short-term / medium-term / long-term.
(draw from [INSIGHT FLAGS], [NEWS], [FILINGS CONTEXT])

## Bottom Line
One sentence. Commit to Bullish / Bearish / Neutral. No buy/sell advice.""" + _FOLLOW_UP_BLOCK

_INTENT_SUMMARIZE_TRADER = """SUMMARY QUERY — full directional analysis for an active trader.
Produce ALL sections where data exists. `##` headers only — NEVER `###`.
Every section must support ONE dominant trade driver. Remove any point that doesn't support the thesis.

## [Company Name] — [Bullish/Bearish/Neutral]: [key trade reason in one phrase]
Example: ## Apple — Bullish: earnings beat confirms re-acceleration, volume surge backs the move

## Price Action
Today's move, volume vs average, 52-week range position. State directional bias + single best reason + timeframe.
(draw from [REAL-TIME DATA])

## Financials
Most recent year. Health verdict + trade implication in one sentence (cash machine / leveraged / burning cash). Cover: revenue trend, margins, FCF yield if derivable.
(draw from [ANNUAL INCOME HISTORY] and [ANNUAL CASH FLOW HISTORY])

## Valuation
P/E, Forward P/E, analyst target with upside/downside %. One sentence: what this means for downside risk.
(draw from [FUNDAMENTALS])

## Analyst Consensus
Buy/Hold/Sell counts, % bullish, conviction level: strong / mixed / weak.
(draw from [FUNDAMENTALS] analyst consensus block)

## Catalysts
Specific recent events with near-term price implication. No vague statements.
(draw from [NEWS] and [FILINGS CONTEXT])

## Historical Pattern
If [HISTORICAL PATTERN] data exists → MUST include: cite period + forward return, state trade implication.
If absent → skip silently.
(draw from [HISTORICAL PATTERN])

## Risks
2–3 risks using `- ` bullet format (NOT numbered), each tied to specific data, each ending with a timeframe tag: short-term / medium-term / long-term.
(draw from [INSIGHT FLAGS], [NEWS], [FILINGS CONTEXT])

## Trade Scenarios
THREE grounded scenarios — each requires TWO specific conditions from the provided data. No generic phrases like "if momentum continues".

**Bull case:** [condition 1 from data] + [condition 2 from data] → [specific price behavior]
**Base case:** [condition 1] + [condition 2 balancing factor] → [expected behavior]
**Bear case:** [condition 1 risk materialises] + [condition 2 amplifier] → [specific downside]

## Trade Signal
One actionable signal with a clear trigger or level if derivable from data.""" + _FOLLOW_UP_BLOCK

# ─────────────────────────────────────────────────────────────────────────────
# Intent → token budget + block map
# ─────────────────────────────────────────────────────────────────────────────

_INTENT_TOKENS: dict[str, int] = {
    "metric":    400,
    "explain":   500,
    "trade":     700,
    "summarize": 2500,
}

_INTENT_BLOCK_MAP: dict[tuple[str, str], str] = {
    ("metric",    "insight"): _INTENT_METRIC,
    ("metric",    "trader"):  _INTENT_METRIC,
    ("explain",   "insight"): _INTENT_EXPLAIN,
    ("explain",   "trader"):  _INTENT_EXPLAIN,
    ("summarize", "insight"): _INTENT_SUMMARIZE_INSIGHT,
    ("summarize", "trader"):  _INTENT_SUMMARIZE_TRADER,
    ("trade",     "insight"): _INTENT_TRADE_INSIGHT,
    ("trade",     "trader"):  _INTENT_TRADE_TRADER,
}

# ─────────────────────────────────────────────────────────────────────────────
# Keyword sets for intent classification
# ─────────────────────────────────────────────────────────────────────────────

_TRADE_KWS = [
    "should i", "worth buying", "good buy", "good investment", "invest in",
    "buy or sell", "entry point", "is it worth", "should i invest", "good time to buy",
    "is it a buy", "worth investing",
]
_SUMM_KWS = [
    "summarize", "summary", "overview", "analyze", "tell me about", "how is",
    "breakdown", "deep dive", "how strong", "assess", "how does it look",
    "give me an overview", "full analysis",
]
# Queries with these words mean "give me a FULL analysis" — don't narrow to a section
# even if section keywords (e.g. "expensive") are also present in the query
_FULL_SUMM_OVERRIDE = frozenset({"analyze", "analysis", "deep dive", "full analysis"})
_EXPLAIN_KWS = [
    "explain", "what does", "how does", "what is a ", "how do ", "define",
    "meaning of", "what are the",
    # Financial concept definitions — "what is [concept]" without company possessive
    "what is free cash flow", "what is fcf", "what is ebitda",
    "what is pe ratio", "what is p/e ratio", "what is forward pe",
    "what is eps", "what is earnings per share",
    "what is rsi", "what is macd", "what is beta",
    "what is market cap", "what is dividend yield",
    "what is gross margin", "what is operating margin", "what is net margin",
    "what is return on equity", "what is roe", "what is debt to equity",
    "what is price to book", "what is revenue", "what is net income",
]
_METRIC_KWS = [
    "what is", "what's", "how much", "show me", "tell me the", "what was",
    "current price", "today's", "52-week",
]

# ─────────────────────────────────────────────────────────────────────────────
# Section-level sub-intent detection — maps focused query → single section
# ─────────────────────────────────────────────────────────────────────────────

_SECTION_KWS: dict[str, list[str]] = {
    "risks":      ["risk", "risks", "downside", "what could go wrong", "biggest risk"],
    "business":   ["business model", "what does it do", "how does it earn", "how does it make money"],
    "cashflow":   ["cash flow", "cash generation", "fcf", "free cash flow"],
    "balance":    ["balance sheet", "debt load", "leverage", "net debt"],
    "valuation":  ["valuation", "overvalued", "undervalued"],
    "analyst":    ["analyst consensus", "analyst view", "what analysts think", "analyst rating"],
    "catalysts":  ["catalyst", "catalysts", "what's the trigger", "upcoming earnings"],
    "historical": ["historical pattern", "past performance", "historically"],
    "news":       ["latest news", "recent news", "what's in the news", "news about",
                   "recent headlines", "what happened", "any news", "any updates",
                   "latest updates", "recent updates", "update on", "news on"],
}

_SECTION_LABELS: dict[str, str] = {
    "risks":      "Key Risks",
    "business":   "The Business",
    "cashflow":   "Cash Flow",
    "balance":    "Balance Sheet",
    "valuation":  "Valuation",
    "analyst":    "Analyst Consensus",
    "catalysts":  "Catalysts / Recent Drivers",
    "historical": "Historical Patterns",
    "news":       "Recent News & Events",
}

_SECTION_DATA_HINTS: dict[str, str] = {
    "risks":      "[INSIGHT FLAGS], [NEWS], [FILINGS CONTEXT], [FUNDAMENTALS]",
    "business":   "[FILINGS CONTEXT], [FUNDAMENTALS]",
    "cashflow":   "[ANNUAL CASH FLOW HISTORY], [FINANCIAL STATEMENTS]",
    "balance":    "[ANNUAL BALANCE SHEET HISTORY], [FUNDAMENTALS]",
    "valuation":  "[FUNDAMENTALS] (PE, Forward PE, analyst target), [REAL-TIME DATA]",
    "analyst":    "[FUNDAMENTALS] analyst consensus block",
    "catalysts":  "[NEWS], [FILINGS CONTEXT]",
    "historical": "[HISTORICAL PATTERN] — cite period and forward return",
    "news":       "[NEWS] and [FILINGS CONTEXT] — cite source, date, and stock implication for each",
}

_SECTION_TOKENS: dict[str, int] = {
    "risks": 700, "business": 400, "cashflow": 600,
    "balance": 600, "valuation": 700, "analyst": 500,
    "catalysts": 700, "historical": 600, "news": 800,
}

# Keyword matching for _enforce_sections — handles insight/trader header variations:
# insight: "Historical Parallels", "What Analysts Think", "Recent Drivers"
# trader:  "Historical Pattern", "Analyst Consensus", "Catalysts"
_SECTION_HEADER_KEYWORDS: dict[str, list[str]] = {
    "risks":      ["risk"],
    "business":   ["business"],
    "cashflow":   ["cash flow", "cash"],
    "balance":    ["balance"],
    "valuation":  ["valuation"],
    "analyst":    ["analyst"],
    "catalysts":  ["catalyst", "recent driver"],
    "news":       ["recent driver", "recent news", "news"],
    "historical": ["historical"],
}


def _detect_sections(q: str) -> list[str]:
    """Return all section keys that match the query (multi-section aware)."""
    matches = []
    for section, kws in _SECTION_KWS.items():
        if any(k in q for k in kws):
            matches.append(section)
    # Lightweight semantic fallback for paraphrased section intent
    if not matches:
        if any(k in q for k in ["downside", "go wrong", "threat"]):
            matches.append("risks")
        if any(k in q for k in ["cheap", "expensive", "priced"]):
            matches.append("valuation")
    return list(dict.fromkeys(matches))  # preserve insertion order, deduplicate


def _classify_response_intent(query: str) -> str:
    q = query.lower().strip()

    if any(k in q for k in _TRADE_KWS):
        return "trade"

    if any(k in q for k in _EXPLAIN_KWS):
        if any(w in q for w in ["apple", "tesla", "aapl", "stock"]):
            if any(k in q for k in ["what is", "how much", "current"]):
                return "metric"
        return "explain"

    if _detect_sections(q):
        return "summarize"

    if any(k in q for k in _SUMM_KWS):
        return "summarize"

    if len(q.split()) <= 4:
        return "metric"

    return "summarize"


def _build_prompt(mode: str, intent: str, sections: list[str] | None = None) -> str:
    """Compose: guardrails + mode reasoning (skipped for metric/explain) + focus + intent instructions.
    focus_block injected BETWEEN mode_base and intent_block — LLM reads constraint before template."""
    intent_block = _INTENT_BLOCK_MAP[(intent, mode)]
    if intent in {"metric", "explain"}:
        return f"""{_BASE_GUARDRAILS}

    STRICT FORMAT:
    - DO NOT generate sections
    - DO NOT summarize the company
    - Answer ONLY the question asked

    {intent_block}"""
    mode_base = _MODE_BASE_TRADER if mode == "trader" else _MODE_BASE_INSIGHT
    focus_block = ""
    if intent == "summarize" and sections:
        labels = [_SECTION_LABELS.get(s, s.upper()) for s in sections]
        data_hints = [_SECTION_DATA_HINTS.get(s, "") for s in sections]
        hints_lines = "\n".join(f"  - {l}: {d}" for l, d in zip(labels, data_hints))
        focus_block = (
            f"CRITICAL FOCUS — USER ASKED ONLY ABOUT: {', '.join(labels).upper()}\n"
            f"- Generate ONLY these sections: {', '.join(labels)}\n"
            f"- Do NOT include any other sections or headers.\n"
            f"- Primary data sources:\n{hints_lines}\n"
            f"- Depth over breadth: be thorough on these sections, not shallow on many."
        )
    if focus_block:
        return f"{_BASE_GUARDRAILS}\n\n{mode_base}\n\n{focus_block}\n\n{intent_block}"
    return f"{_BASE_GUARDRAILS}\n\n{mode_base}\n\n{intent_block}"


# ─────────────────────────────────────────────────────────────────────────────
# Post-processors
# ─────────────────────────────────────────────────────────────────────────────

def _sanitize_headers(text: str) -> str:
    """Downgrade ### or deeper to ## — LLM occasionally ignores the rule."""
    return re.sub(r"^#{3,}\s+", "## ", text, flags=re.MULTILINE)


def _fix_markdown_headers(text: str) -> str:
    """Ensure ## headers are on their own line with exactly one blank line before them."""
    # Consume non-newline char + any trailing whitespace before ##, insert \n\n between
    text = re.sub(r"([^\n])\s*(##\s+)", r"\1\n\n\2", text)
    # Collapse triple+ newlines anywhere
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _validate_metric_output(text: str) -> str:
    """Metric responses MUST contain a digit. LLM sometimes drifts into a definition
    paragraph with no number — that's worse than admitting the data is absent."""
    if not re.search(r"\d", text):
        return "The exact value isn't available in the current data snapshot — this metric may not have been retrieved in this request. Try asking a broader question or refresh."
    return text


def _is_degenerate(text: str) -> bool:
    """Detect bad LLM outputs that warrant a retry."""
    t = text.strip()
    if len(t) < 20:
        return True
    if t.count("##") > 15:      # runaway structure
        return True
    if "I couldn't generate" in t:
        return True
    return False


def _apply_post_processors(text: str) -> str:
    return _fix_markdown_headers(_sanitize_headers(text))


def _extract_suggestions(text: str, intent: str) -> tuple[str, list[str]]:
    """Split LLM output into (response_text, follow_up_questions). All intents can produce suggestions."""
    if "---SUGGESTIONS---" not in text:
        return _apply_post_processors(text.strip()), []
    parts = text.split("---SUGGESTIONS---", 1)
    response = _apply_post_processors(parts[0].strip())
    questions = [q.strip() for q in parts[1].strip().splitlines() if q.strip()][:5]
    return response, questions


def _enforce_sections(text: str, sections: list[str]) -> str:
    """Hard-strip ## sections not in the requested set.
    Uses keyword matching so insight/trader header variants both match
    (e.g. 'Historical Parallels' and 'Historical Pattern' both contain 'historical').
    Safety net: if result < 30% of original, fall back to original."""
    if not sections:
        return text
    # Collect all keywords for requested sections
    allowed_kws: list[str] = []
    for s in sections:
        allowed_kws.extend(_SECTION_HEADER_KEYWORDS.get(s, [_SECTION_LABELS.get(s, s).lower()]))
    lines = text.splitlines()
    keep: list[str] = []
    in_allowed = False
    for line in lines:
        if line.strip().startswith("##"):
            header = re.sub(r"^#{2,}\s*", "", line).strip().lower()
            in_allowed = any(kw in header for kw in allowed_kws)
        if in_allowed:
            keep.append(line)
    result = "\n".join(keep).strip()
    # Only fall back if nothing matched at all (completely different header wording)
    # A single focused section is much shorter than full text — that's expected and correct
    if not result:
        return text
    return result

def _enforce_metric_strict(text: str) -> str:
    """Kill any accidental structured output for metric queries."""
    text = re.sub(r"##.*", "", text, flags=re.DOTALL).strip()
    return _validate_metric_output(text)


def _enforce_explain_strict(text: str) -> str:
    """Force short, clean explain responses."""
    text = re.sub(r"##.*", "", text, flags=re.DOTALL).strip()
    sentences = re.split(r'(?<=[.!?]) +', text)
    return " ".join(sentences[:4]).strip()


def _generate_fallback_suggestions(query: str, ticker: str) -> list[str]:
    base = ticker or "the company"
    return [
        f"{base} risks?",
        f"{base} valuation?",
        f"{base} growth outlook?"
    ]


def _enforce_units(text: str) -> str:
    """Ensure large numbers aren't unitless (light heuristic)."""
    def repl(match):
        num = int(match.group(1))
        if num > 1_000_000_000:
            return f"${num/1_000_000_000:.1f}B"
        if num > 1_000_000:
            return f"${num/1_000_000:.1f}M"
        return match.group(1)

    return re.sub(r"\b(\d{6,})\b", repl, text)


# ─────────────────────────────────────────────────────────────────────────────
# Groq call
# ─────────────────────────────────────────────────────────────────────────────

def _call_groq(
    client: Groq,
    model: str,
    system_prompt: str,
    fused_context: str,
    max_tokens: int,
) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": fused_context},
        ],
        max_tokens=max_tokens,
        temperature=_TEMPERATURE,
    )
    return resp.choices[0].message.content or ""


# ─────────────────────────────────────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────────────────────────────────────

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
        intent_for_empty = _classify_response_intent(query)
        if intent_for_empty == "metric":
            return {
                "response": "The exact value isn't available in the current data.",
                "followup_questions": [],
            }
        return {
            "response": "I don't have enough data to answer that query.",
            "followup_questions": [],
        }

    response_intent = _classify_response_intent(query)
    q_lower = query.lower().strip()
    # Suppress section narrowing when the query explicitly requests a full analysis
    # e.g. "Apple looks expensive but growing fast — analyze" has "analyze" → full summary, not just valuation
    _want_full_summ = any(k in q_lower for k in _FULL_SUMM_OVERRIDE)
    sections = (
        _detect_sections(q_lower)
        if response_intent == "summarize" and not _want_full_summ
        else []
    )
    system_prompt = _build_prompt(user_mode, response_intent, sections)
    max_tokens = _INTENT_TOKENS[response_intent]
    if sections:
        max_tokens = max(_SECTION_TOKENS.get(s, 700) for s in sections)
    max_tokens = int(max_tokens * 1.2)  # 20% buffer — prevents mid-sentence token truncation

    prompt_chars = len(system_prompt)
    log.info("response_prompt_size", chars=prompt_chars, intent=response_intent, mode=user_mode, sections=sections)
    if prompt_chars > 7000:
        log.warning("prompt_too_large", chars=prompt_chars, intent=response_intent)
        if response_intent == "summarize" and not sections:
            max_tokens = 1800  # auto-compress only for full summaries, not focused sections

    # Cache key includes intent + context hash to prevent cross-intent and stale-context hits
    import hashlib
    ctx_hash = hashlib.md5(fused_context[:1000].encode()).hexdigest()[:8]
    cache_hit = False
    text = ""
    if ticker and query and not is_volatile_query(query):
        key = cache_key(ticker, query, f"{user_mode}:{response_intent}:{ctx_hash}")
        cached = get_cached(key, current_pct)
        if cached:
            log.info("response_cache_hit", ticker=ticker, user_mode=user_mode, intent=response_intent)
            text = cached
            cache_hit = True

    if not cache_hit:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        model_used = _GROQ_MODEL_PRIMARY
        try:
            text = _call_groq(client, _GROQ_MODEL_PRIMARY, system_prompt, fused_context, max_tokens)
        except Exception as exc:
            err_str = str(exc)
            if "429" in err_str or "rate_limit" in err_str.lower():
                log.warning("groq_primary_rate_limited_falling_back_to_8b", error=err_str[:120])
                try:
                    text = _call_groq(client, _GROQ_MODEL_FALLBACK, system_prompt, fused_context, max_tokens)
                    model_used = _GROQ_MODEL_FALLBACK
                except Exception as fallback_exc:
                    log.error("groq_fallback_also_failed", error=str(fallback_exc))
                    text = "I encountered an error generating the analysis. Please try again."
            else:
                log.error("groq_generation_failed", error=err_str)
                text = "I encountered an error generating the analysis. Please try again."

        # Quality retry — if primary returned degenerate output, retry with fallback model
        if text and _is_degenerate(text) and model_used == _GROQ_MODEL_PRIMARY:
            log.warning("groq_degenerate_response_retrying_with_fallback", chars=len(text.strip()))
            try:
                text = _call_groq(client, _GROQ_MODEL_FALLBACK, system_prompt, fused_context, max_tokens)
                model_used = _GROQ_MODEL_FALLBACK
            except Exception as retry_exc:
                log.error("groq_quality_retry_failed", error=str(retry_exc))
                text = "I couldn't generate a reliable answer for that query. Please try rephrasing."

        if text and model_used == _GROQ_MODEL_PRIMARY and ticker and query and not is_volatile_query(query):
            set_cached(cache_key(ticker, query, f"{user_mode}:{response_intent}:{ctx_hash}"), text, current_pct)

    text, suggestions = _extract_suggestions(text, response_intent)

    # HARD INTENT ENFORCEMENT
    if response_intent == "metric":
        text = _enforce_metric_strict(text)

        # If still too long → force fallback
        if len(text.split()) > 80:
            return {
                "response": "The exact value isn't available in the current data.",
                "followup_questions": suggestions or _generate_fallback_suggestions(query, ticker),
            }

    elif response_intent == "explain":
        text = _enforce_explain_strict(text)

    # SECTION ENFORCEMENT (only for summarize)
    if sections:
        text = _enforce_sections(text, sections)

    # UNIT ENFORCEMENT
    text = _enforce_units(text)

    # FALLBACK SUGGESTIONS (universal)
    if len(suggestions) < 3:
        suggestions = _generate_fallback_suggestions(query, ticker)

    text = apply_output_guardrail(
        response=text,
        fused_context=fused_context,
        confidence_score=confidence,
        disclaimer_text=disclaimer,
        locale=locale,
    )

    # Terminal safety net — never send a blank response; surface partial context instead
    if not text or len(text.strip()) < 15:
        log.warning("empty_response_after_guardrail", intent=response_intent, ticker=ticker)
        _fc_lines = [l.strip() for l in fused_context.splitlines()
                     if l.strip() and not l.strip().startswith("[") and len(l.strip()) > 20]
        if _fc_lines:
            _preview = " ".join(_fc_lines[:2])[:300]
            text = f"The available data is limited. Here's what I can see: {_preview}"
        else:
            text = "Insufficient data to generate a response for this query. Please try a more specific question."

    log.info(
        "response_ok",
        chars=len(text),
        confidence=confidence,
        cache_hit=cache_hit,
        user_mode=user_mode,
        response_intent=response_intent,
        sections=sections,
        max_tokens=max_tokens,
        suggestions=len(suggestions),
    )
    return {"response": text, "followup_questions": suggestions}
