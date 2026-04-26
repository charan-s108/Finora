"""Fusion node — assembles structured data context for the response LLM."""
from __future__ import annotations

import os

import structlog

from graph.state import FiNoraState
from guardrails.disclaimers import get_disclaimer

log = structlog.get_logger()

_SUMMARY_TRIGGERS = {
    "summarize", "summary", "explain", "overview", "what's happening",
    "whats happening", "tell me about", "breakdown", "analyse", "analyze",
    "give me a", "what do you think", "how is", "how's",
}


def _is_summary_query(query: str) -> bool:
    q = query.lower().strip()
    return any(trigger in q for trigger in _SUMMARY_TRIGGERS)


def _currency_sym(currency: str) -> str:
    return "₹" if currency == "INR" else "$"


def _fmt_realtime(rt: dict | None, currency: str = "USD") -> str:
    if not rt or not rt.get("price"):
        return "[REAL-TIME DATA UNAVAILABLE]"
    sym = _currency_sym(currency)
    ticker = rt.get("ticker", "")
    price = rt.get("price")
    change = rt.get("change")
    pct = rt.get("pct_change")
    vol = rt.get("volume")
    avg_vol = rt.get("avg_volume_30d")
    vol_ratio = round(vol / avg_vol, 1) if vol and avg_vol else None

    lines = [f"{ticker}: {sym}{price:.2f} ({pct:+.2f}%)" if price and pct else f"{ticker}: {sym}{price}"]
    if change:
        lines.append(f"Change: {sym}{change:+.4f}")
    if vol_ratio is not None:
        lines.append(f"Volume: {vol:,} ({vol_ratio}x 30d avg)")
    w52h = rt.get("week_52_high")
    w52l = rt.get("week_52_low")
    if w52h and w52l:
        lines.append(f"52W Range: {sym}{w52l:.2f} - {sym}{w52h:.2f}")

    return "\n".join(lines)


def _fmt_historical_patterns(patterns: list[dict]) -> str:
    """Format always-available historical patterns fetched alongside realtime data."""
    if not patterns:
        return ""
    top = patterns[:2]
    lines = [f"[HISTORICAL PATTERNS — {len(top)} events]"]
    for i, p in enumerate(top, 1):
        parts = [f"[{i}]"]
        if p.get("event_type"):
            parts.append(p["event_type"].replace("_", " ").title())
        if p.get("date_range"):
            parts.append(f"({p['date_range']})")
        if p.get("return_pct") is not None:
            parts.append(f"fwd return: {p['return_pct']:+.1f}%")
        if p.get("text"):
            parts.append(f"— {p['text'][:120]}")
        lines.append(" ".join(parts))
    return "\n".join(lines)


_CHUNK_TEXT_LIMIT = int(os.getenv("RAG_CHUNK_TEXT_LIMIT", "400"))
_MAX_NEWS_CHUNKS = int(os.getenv("RAG_MAX_NEWS_CHUNKS", "4"))
_MAX_HIST_CHUNKS = int(os.getenv("RAG_MAX_HIST_CHUNKS", "3"))


def _fmt_chunks(chunks: list[dict], label: str, max_chunks: int = _MAX_NEWS_CHUNKS) -> str:
    if not chunks:
        return f"[NO {label.upper()} DATA]"
    lines = [f"[{label.upper()} - {min(len(chunks), max_chunks)} sources]"]
    for i, ch in enumerate(chunks[:max_chunks], 1):
        source = ch.get("source", ch.get("url", "unknown"))
        date = ch.get("published_at", ch.get("start_date", ch.get("date_range", "")))
        text = ch.get("text", "")[:_CHUNK_TEXT_LIMIT]
        lines.append(f"[{i}] {source} ({date}): {text}")
    return "\n".join(lines)


def _fmt_sector_context(sc: dict | None, currency: str = "USD") -> str:
    if not sc:
        return ""
    sym = _currency_sym(currency)
    lines = []

    sector = sc.get("sector")
    etf = sc.get("sector_etf")
    if sector:
        header = f"[SECTOR CONTEXT — {sector}]"
        if etf:
            pct = etf.get("return_pct", 0)
            price = etf.get("price")
            etf_name = etf.get("etf", "")
            price_str = f" ({sym}{price:.2f})" if price else ""
            header += f"\nSector ETF ({etf_name}){price_str}: {pct:+.2f}% today"
        lines.append(header)

    all_etfs = sc.get("all_sector_etfs", [])
    if all_etfs:
        sorted_etfs = sorted(all_etfs, key=lambda x: x.get("return_pct", 0), reverse=True)
        etf_parts = [
            f"{e['sector']} ({e['etf']}): {e.get('return_pct', 0):+.2f}%"
            for e in sorted_etfs[:6]
        ]
        lines.append("Sector performance today:\n" + "\n".join(etf_parts))

    similar = sc.get("similar_stocks", [])
    if similar:
        sim_parts = [
            f"- {s['ticker']} ({s['exchange']}): {s['name']}"
            for s in similar[:6]
        ]
        lines.append(f"Similar stocks in {sector or 'sector'}:\n" + "\n".join(sim_parts))

    return "\n".join(lines)


def _fmt_fundamentals(fd: dict | None, currency: str = "USD") -> str:
    if not fd:
        return "[FUNDAMENTAL DATA UNAVAILABLE]"
    sym = _currency_sym(currency)
    parts: list[str] = []
    if fd.get("pe"):
        parts.append(f"PE: {fd['pe']:.1f}")
    if fd.get("forward_pe"):
        parts.append(f"Forward PE: {fd['forward_pe']:.1f}")
    if fd.get("eps"):
        parts.append(f"EPS: {sym}{fd['eps']:.2f}")
    if fd.get("analyst_target"):
        parts.append(f"Analyst target: {sym}{fd['analyst_target']:.2f}")
    if fd.get("recommendation"):
        parts.append(f"Consensus: {fd['recommendation'].upper()}")
    if fd.get("profit_margins"):
        parts.append(f"Net margin: {fd['profit_margins']*100:.1f}%")
    if fd.get("beta"):
        parts.append(f"Beta: {fd['beta']:.2f}")
    if fd.get("revenue"):
        parts.append(f"Revenue: {sym}{fd['revenue']/1e9:.1f}B")
    if fd.get("market_cap"):
        mc = fd["market_cap"]
        mc_str = f"{sym}{mc/1e12:.2f}T" if mc >= 1e12 else f"{sym}{mc/1e9:.1f}B"
        parts.append(f"Mkt Cap: {mc_str}")

    consensus = fd.get("analyst_consensus") or {}
    buy = consensus.get("buy", 0) or 0
    hold = consensus.get("hold", 0) or 0
    sell = consensus.get("sell", 0) or 0
    if buy or hold or sell:
        total = buy + hold + sell
        buy_pct = round(buy / total * 100) if total else 0
        parts.append(f"Analysts: {buy} Buy / {hold} Hold / {sell} Sell ({buy_pct}% bullish)")

    return " | ".join(parts) if parts else "[LIMITED FUNDAMENTAL DATA]"


def _compute_insight_flags(state: FiNoraState) -> list[str]:
    """Pre-compute interpretive signals grounded in data — no hallucination possible."""
    flags: list[str] = []
    rt = state.get("realtime_context") or {}
    fd = state.get("fundamental_data") or {}
    sym = _currency_sym(state.get("currency", "USD"))

    # Volume anomaly
    vol = rt.get("volume")
    avg_vol = rt.get("avg_volume_30d")
    if vol and avg_vol and avg_vol > 0:
        vol_z = vol / avg_vol
        if vol_z >= 2.5:
            flags.append(f"Volume spike: {vol_z:.1f}x 30-day average — unusual institutional activity likely")
        elif vol_z <= 0.4:
            flags.append("Volume well below average — low conviction move, may not be sustained")

    # PE interpretation
    pe = fd.get("pe")
    fpe = fd.get("forward_pe")
    if pe and pe > 0:
        if pe > 40:
            flags.append(f"PE of {pe:.1f} — premium valuation, priced for high earnings growth expectations")
        elif pe < 12:
            flags.append(f"PE of {pe:.1f} — below typical market average, may signal undervaluation or elevated risk")
        if fpe and fpe > 0:
            ratio = fpe / pe
            if ratio < 0.80:
                flags.append(
                    f"Forward PE ({fpe:.1f}) significantly below trailing ({pe:.1f}) — "
                    "earnings growth expected ahead"
                )
            elif ratio > 1.20:
                flags.append(
                    f"Forward PE ({fpe:.1f}) above trailing ({pe:.1f}) — "
                    "earnings expected to slow or decline"
                )

    # 52W range position
    price = rt.get("price")
    w52h = rt.get("week_52_high") or fd.get("week_52_high")
    w52l = rt.get("week_52_low") or fd.get("week_52_low")
    if price and w52h and w52l and w52h > w52l:
        pos_pct = ((price - w52l) / (w52h - w52l)) * 100
        if pos_pct >= 95:
            flags.append(f"Near 52-week high ({sym}{w52h:.2f}) — potential resistance zone")
        elif pos_pct <= 5:
            flags.append(f"Near 52-week low ({sym}{w52l:.2f}) — potential support zone")
        elif pos_pct >= 75:
            flags.append(f"Upper quartile of 52-week range ({pos_pct:.0f}% from low) — relative strength")
        elif pos_pct <= 25:
            flags.append(f"Lower quartile of 52-week range ({pos_pct:.0f}% from low) — relative weakness")

    # Analyst consensus
    consensus = fd.get("analyst_consensus") or {}
    buy = consensus.get("buy", 0) or 0
    hold = consensus.get("hold", 0) or 0
    sell = consensus.get("sell", 0) or 0
    total = buy + hold + sell
    if total >= 3:
        buy_pct = buy / total
        if buy_pct >= 0.75:
            flags.append(f"Strong buy consensus: {round(buy_pct*100)}% of {total} analysts rate Buy")
        elif buy_pct <= 0.25:
            flags.append(f"Weak buy consensus: only {round(buy_pct*100)}% of {total} analysts rate Buy")

    # Price vs analyst target
    target = fd.get("analyst_target") or (consensus.get("avg_target") if consensus else None)
    if price and target and target > 0:
        upside = ((target - price) / price) * 100
        if upside >= 15:
            flags.append(f"Analyst target ({sym}{target:.2f}) implies {upside:.0f}% upside from current price")
        elif upside <= -10:
            flags.append(f"Current price {abs(upside):.0f}% above consensus analyst target ({sym}{target:.2f})")

    # Profit margin
    margin = fd.get("profit_margins")
    if margin is not None:
        if margin >= 0.25:
            flags.append(f"High net margin of {margin*100:.1f}% — strong pricing power or operational efficiency")
        elif margin < 0.05:
            flags.append(f"Thin net margin of {margin*100:.1f}% — highly sensitive to cost pressures")

    # Beta
    beta = fd.get("beta")
    if beta is not None:
        if beta >= 1.5:
            flags.append(f"High beta ({beta:.2f}) — moves significantly more than the broader market")
        elif beta <= 0.5:
            flags.append(f"Low beta ({beta:.2f}) — defensive stock with low market correlation")

    return flags


def _compute_narrative_hint(state: FiNoraState) -> str:
    """Single most important signal — used to anchor the opening narrative sentence."""
    rt = state.get("realtime_context") or {}
    fd = state.get("fundamental_data") or {}

    pct = rt.get("pct_change")
    vol = rt.get("volume")
    avg_vol = rt.get("avg_volume_30d")
    price = rt.get("price")
    w52h = rt.get("week_52_high")
    w52l = rt.get("week_52_low")
    consensus = (fd.get("analyst_consensus") or {})
    buy = consensus.get("buy", 0) or 0
    hold = consensus.get("hold", 0) or 0
    sell = consensus.get("sell", 0) or 0
    total = buy + hold + sell

    # Priority order: large price move > volume spike > 52W extreme > consensus
    if pct is not None and abs(pct) >= 3.0:
        direction = "sharp_upward_move" if pct > 0 else "sharp_downward_move"
        return direction

    if vol and avg_vol and avg_vol > 0 and (vol / avg_vol) >= 2.5:
        return "high_volume_move"

    if price and w52h and w52l and w52h > w52l:
        pos = (price - w52l) / (w52h - w52l)
        if pos >= 0.95:
            return "near_52w_high"
        if pos <= 0.05:
            return "near_52w_low"

    if total >= 3:
        if buy / total >= 0.75:
            return "analyst_strongly_bullish"
        if buy / total <= 0.25:
            return "analyst_bearish"

    if pct is not None:
        if pct >= 1.0:
            return "mild_upward_move"
        if pct <= -1.0:
            return "mild_downward_move"

    return "consolidating"


def _compute_confidence_level(state: FiNoraState) -> str:
    """Derived confidence: how strongly do signals agree?"""
    rt = state.get("realtime_context") or {}
    fd = state.get("fundamental_data") or {}

    strong_signals = 0

    pct = rt.get("pct_change")
    if pct is not None and abs(pct) >= 2.0:
        strong_signals += 1

    vol = rt.get("volume")
    avg_vol = rt.get("avg_volume_30d")
    if vol and avg_vol and avg_vol > 0 and (vol / avg_vol) >= 2.0:
        strong_signals += 1

    price = rt.get("price")
    w52h = rt.get("week_52_high")
    w52l = rt.get("week_52_low")
    if price and w52h and w52l and w52h > w52l:
        pos = (price - w52l) / (w52h - w52l)
        if pos >= 0.85 or pos <= 0.15:
            strong_signals += 1

    consensus = (fd.get("analyst_consensus") or {})
    buy = consensus.get("buy", 0) or 0
    hold = consensus.get("hold", 0) or 0
    sell = consensus.get("sell", 0) or 0
    total = buy + hold + sell
    if total >= 3 and (buy / total >= 0.70 or buy / total <= 0.30):
        strong_signals += 1

    has_news = bool(state.get("news_chunks"))
    has_historical = bool(state.get("historical_chunks"))
    has_fundamentals = bool(fd)
    data_sources = sum([bool(rt), has_news, has_historical, has_fundamentals])

    if strong_signals >= 3 and data_sources >= 3:
        return "high"
    if strong_signals >= 1 and data_sources >= 2:
        return "medium"
    return "low"


def _compute_conflict(state: FiNoraState) -> tuple[bool, str]:
    """Detect meaningful signal conflicts — price vs analyst, short vs long-term."""
    rt = state.get("realtime_context") or {}
    fd = state.get("fundamental_data") or {}

    pct = rt.get("pct_change")
    consensus = (fd.get("analyst_consensus") or {})
    buy = consensus.get("buy", 0) or 0
    hold = consensus.get("hold", 0) or 0
    sell = consensus.get("sell", 0) or 0
    total = buy + hold + sell

    price = rt.get("price")
    w52h = rt.get("week_52_high")
    w52l = rt.get("week_52_low")

    # Price falling but analysts strongly bullish
    if pct is not None and pct <= -2.0 and total >= 3 and buy / total >= 0.65:
        return True, "price_down_but_analyst_bullish"

    # Price rising sharply but analysts mostly bearish/hold
    if pct is not None and pct >= 2.0 and total >= 3 and (hold + sell) / total >= 0.65:
        return True, "price_up_but_analyst_cautious"

    # Near 52W low but strong buy consensus
    if price and w52h and w52l and w52h > w52l and total >= 3:
        pos = (price - w52l) / (w52h - w52l)
        if pos <= 0.15 and buy / total >= 0.65:
            return True, "near_52w_low_but_analyst_bullish"

    # Near 52W high but analyst target below current price
    target = fd.get("analyst_target") or (consensus.get("avg_target") if consensus else None)
    if price and target and w52h and w52l and w52h > w52l:
        pos = (price - w52l) / (w52h - w52l)
        if pos >= 0.85 and target < price:
            return True, "near_52w_high_but_target_below_price"

    return False, ""


def _compute_price_trend(rt: dict | None, fd: dict | None) -> dict[str, str]:
    signals: dict[str, str] = {}
    if not rt:
        return signals

    pct = rt.get("pct_change")
    if pct is not None:
        if pct >= 2.0:
            signals["short_term"] = f"Upward (+{pct:.1f}% today)"
        elif pct <= -2.0:
            signals["short_term"] = f"Downward ({pct:.1f}% today)"
        else:
            signals["short_term"] = f"Flat ({pct:+.1f}% today)"

    price = rt.get("price")
    w52h = rt.get("week_52_high")
    w52l = rt.get("week_52_low")
    if price and w52h and w52l and w52h > w52l:
        pos = (price - w52l) / (w52h - w52l)
        if pos >= 0.7:
            signals["long_term"] = "Near 52-week high — longer-term uptrend"
        elif pos <= 0.3:
            signals["long_term"] = "Near 52-week low — longer-term downtrend or consolidation"
        else:
            signals["long_term"] = "Mid-range of 52-week band"

    beta = (fd or {}).get("beta")
    if beta is not None:
        if beta >= 1.3:
            signals["volatility"] = f"High ({beta:.2f} beta) — amplified market moves"
        elif beta <= 0.7:
            signals["volatility"] = f"Low ({beta:.2f} beta) — defensive, dampened moves"
        else:
            signals["volatility"] = f"Moderate ({beta:.2f} beta)"

    return signals


def _compute_confidence(state: FiNoraState) -> float:
    score = 0.0
    if state.get("realtime_context") and state["realtime_context"].get("price"):
        score += 0.3
    if state.get("news_chunks"):
        score += 0.3
    if state.get("historical_chunks"):
        score += 0.25
    if state.get("fundamental_data"):
        score += 0.15
    return min(round(score, 2), 1.0)


def _build_data_context(state: FiNoraState) -> str:
    """Pure data context — no behavioral instructions. Used as the user message."""
    ticker = state.get("ticker", "")
    company_name = state.get("company_name") or ticker
    currency = state.get("currency") or "USD"
    history = state.get("conversation_history", [])

    rt = state.get("realtime_context")
    fd = state.get("fundamental_data")
    insight_flags = _compute_insight_flags(state)
    trend = _compute_price_trend(rt, fd)
    narrative_hint = _compute_narrative_hint(state)
    confidence_level = _compute_confidence_level(state)
    has_conflict, conflict_reason = _compute_conflict(state)
    uncertainty_flag = confidence_level == "low" or (has_conflict and confidence_level != "high")

    rt_section = _fmt_realtime(rt, currency)
    news_section = _fmt_chunks(state.get("news_chunks", []), "NEWS")

    # Historical: prefer deep RAG chunks (historical_rag_node) when intent fired,
    # otherwise use always-available patterns fetched alongside realtime data
    rag_hist = state.get("historical_chunks", [])
    if rag_hist:
        hist_section = _fmt_chunks(rag_hist, "HISTORICAL PATTERN", max_chunks=_MAX_HIST_CHUNKS)
    else:
        # Always-available fallback: fetched in realtime_node concurrently
        rt_patterns = (rt or {}).get("historical_patterns", [])
        hist_section = _fmt_historical_patterns(rt_patterns)

    fund_section = _fmt_fundamentals(fd, currency)
    sector_section = _fmt_sector_context(state.get("sector_context"), currency)

    flags_text = "\n".join(f"- {f}" for f in insight_flags[:4]) if insight_flags else "No significant flags."
    trend_text = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in trend.items()
    ) if trend else "Trend data unavailable."

    conv_section = ""
    if history:
        recent = history[-4:]
        conv_lines = [f"{m['role'].upper()}: {m['content'][:200]}" for m in recent]
        conv_section = "[CONVERSATION HISTORY]\n" + "\n".join(conv_lines) + "\n\n"

    # Translate internal labels → natural language before sending to LLM
    # This prevents label leakage ("dominant signal suggests", "uncertainty flag")
    _HINT_TO_NL = {
        "sharp_downward_move":   "The stock is experiencing a sharp decline today.",
        "sharp_upward_move":     "The stock is surging sharply today.",
        "high_volume_move":      "Unusually high trading volume is the dominant signal today.",
        "near_52w_high":         "The stock is trading near its 52-week high.",
        "near_52w_low":          "The stock is trading near its 52-week low.",
        "analyst_strongly_bullish": "Analyst consensus is strongly bullish.",
        "analyst_bearish":       "Analyst consensus is leaning bearish.",
        "mild_upward_move":      "The stock is seeing a mild upward move today.",
        "mild_downward_move":    "The stock is seeing a mild decline today.",
        "consolidating":         "No strong directional signal is present — the stock is consolidating.",
    }
    market_context = _HINT_TO_NL.get(narrative_hint, "Market context is unclear.")

    _CONFIDENCE_TO_POSTURE = {
        "high":   "Be direct. State conclusions without hedging.",
        "medium": "Be measured. Use 'data shows' or 'current price action shows' — not 'suggests' or 'indicates'.",
        "low":    "Be cautious. Avoid directional conclusions. Acknowledge limited signal clearly.",
    }
    response_posture = _CONFIDENCE_TO_POSTURE.get(confidence_level, "Be cautious. Avoid strong conclusions.")

    if uncertainty_flag:
        response_posture += " No strong signal — do not construct a directional narrative."

    if has_conflict:
        _CONFLICT_NL = {
            "price_down_but_analyst_bullish":      "Price is declining but analyst consensus is bullish — name this divergence explicitly.",
            "price_up_but_analyst_cautious":       "Price is rising but analysts are cautious — name this divergence explicitly.",
            "near_52w_low_but_analyst_bullish":    "Stock is near 52-week lows but analysts rate it bullish — name this divergence explicitly.",
            "near_52w_high_but_target_below_price":"Stock is near 52-week highs but analyst target is below current price — name this divergence explicitly.",
        }
        conflict_text = _CONFLICT_NL.get(conflict_reason, f"Signal divergence detected: {conflict_reason.replace('_', ' ')}.")
    else:
        conflict_text = ""

    return f"""{conv_section}STOCK: {company_name} ({ticker}) | Currency: {currency}

[MARKET CONTEXT — anchor your opening sentence here]
{market_context}
{f"[SIGNAL DIVERGENCE — acknowledge this in your narrative]{chr(10)}{conflict_text}" if conflict_text else ""}
[RESPONSE POSTURE]
{response_posture}

[REAL-TIME DATA]
{rt_section}

[INSIGHT FLAGS]
{flags_text}

[TREND SIGNALS]
{trend_text}

[FUNDAMENTALS]
{fund_section}

{news_section}

{hist_section}
{chr(10) + sector_section if sector_section else ""}"""


def fusion_node(state: FiNoraState) -> dict:
    query = state["query"]
    ticker = state.get("ticker", "")
    is_summary = _is_summary_query(query)

    data_context = _build_data_context(state)

    if is_summary:
        task = (
            "TASK: Explain what is happening with this stock right now, "
            "as if the user just opened the stock dashboard. "
            "Use the structured output format from your instructions."
        )
    else:
        task = f"QUESTION: {query}"

    fused = f"{data_context}\n\n{task}"

    confidence = _compute_confidence(state)
    disclaimer = get_disclaimer(os.getenv("DISCLAIMER_LOCALE", "IN"))

    citations: list[dict] = []
    for ch in (state.get("news_chunks") or [])[:5]:
        if ch.get("url"):
            citations.append({
                "url": ch["url"],
                "title": ch.get("title", ""),
                "source": ch.get("source", ""),
                "time": ch.get("published_at", ""),
            })

    log.info(
        "fusion_done",
        ticker=ticker,
        mode="summary" if is_summary else "focused",
        user_mode=state.get("user_mode", "insight"),
        confidence=confidence,
        news=len(state.get("news_chunks") or []),
        historical=len(state.get("historical_chunks") or []),
    )

    return {
        "fused_context": fused,
        "confidence_score": confidence,
        "disclaimer_text": disclaimer,
        "citations": citations,
    }
