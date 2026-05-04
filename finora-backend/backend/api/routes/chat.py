import json
import os
import re
import uuid
from typing import AsyncIterator

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.api.middleware.rate_limit import limiter
from backend.graph.nodes.response_cache import cache_key as _resp_cache_key, get_cached as _resp_get_cached, is_volatile_query as _resp_is_volatile
from backend.rag.ingestion.universe import universe

log = structlog.get_logger()
router = APIRouter(tags=["chat"])


def _parse_chart_timeframe(query: str) -> tuple[str, str, str]:
    """
    Returns (range_str, interval, label) for fetch_ohlcv based on query text.
    Handles standard timeframes, custom day counts, and date ranges.
    """
    q = query.lower()

    # Custom date range: "from 2025-01-01 to 2025-03-31" or "from jan 1 to mar 31"
    date_range = re.search(
        r"from\s+(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})", q
    )
    if date_range:
        # Yahoo doesn't support arbitrary date ranges via range_str easily;
        # fall back to period calculation
        from datetime import date
        try:
            start = date.fromisoformat(date_range.group(1))
            end = date.fromisoformat(date_range.group(2))
            days = (end - start).days
            if days <= 7:
                return (f"{days}d", "5m", f"{days}D")
            elif days <= 90:
                return (f"{days}d", "1d", f"{days}D")
            else:
                return (f"{days}d", "1wk", f"{days}D")
        except ValueError:
            pass

    # Custom N days: "20 days", "45 days", "past 10 days"
    n_days = re.search(r"(\d+)\s*day", q)
    if n_days:
        d = int(n_days.group(1))
        d = max(1, min(d, 365))
        interval = "5m" if d == 1 else "1d" if d <= 90 else "1wk"
        return (f"{d}d", interval, f"{d}D")

    # N weeks
    n_weeks = re.search(r"(\d+)\s*week", q)
    if n_weeks:
        w = int(n_weeks.group(1))
        w = max(1, min(w, 52))
        days = w * 7
        interval = "30m" if w == 1 else "1d"
        return (f"{days}d", interval, f"{w}W")

    # N months
    n_months = re.search(r"(\d+)\s*month", q)
    if n_months:
        m = int(n_months.group(1))
        m = max(1, min(m, 60))
        interval = "1d" if m <= 6 else "1wk"
        return (f"{m}mo", interval, f"{m}M")

    # N years
    n_years = re.search(r"(\d+)\s*year", q)
    if n_years:
        y = int(n_years.group(1))
        y = max(1, min(y, 20))
        interval = "1wk" if y <= 5 else "1mo"
        return (f"{y}y", interval, f"{y}Y")

    # Named timeframes
    if any(x in q for x in ("intraday", "today", "1d", "1 day", "one day",
                             "suddenly", "crashing", "crashed", "surging", "surged",
                             "dropped", "spiked", "right now", "happening now")):
        return ("1d", "5m", "1D")
    if any(x in q for x in ("this week", "1w", "1 week", "one week", "past week", "7 day")):
        return ("5d", "30m", "1W")
    if any(x in q for x in ("3m", "3 month", "three month", "quarter", "quarterly")):
        return ("3mo", "1d", "3M")
    if any(x in q for x in ("6m", "6 month", "six month", "half year")):
        return ("6mo", "1d", "6M")
    if any(x in q for x in ("1y", "1 year", "one year", "past year", "this year", "ytd", "annual")):
        return ("1y", "1wk", "1Y")
    if any(x in q for x in ("3y", "3 year", "three year")):
        return ("3y", "1wk", "3Y")
    if any(x in q for x in ("5y", "5 year", "five year")):
        return ("5y", "1wk", "5Y")
    if any(x in q for x in ("all time", "all-time", "max", "20 year", "full history")):
        return ("20y", "1mo", "ALL")

    # Default: 1 month
    return ("1mo", "1d", "1M")

MAX_CONVERSATION_TURNS = int(os.getenv("MAX_CONVERSATION_TURNS", "50"))


class ConversationTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    query: str = Field(..., max_length=500)
    ticker: str = Field(default="")
    conversation_history: list[ConversationTurn] = Field(default_factory=list)
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_mode: str = Field(default="insight", pattern="^(insight|trader)$")


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


async def _stream_graph(req: ChatRequest) -> AsyncIterator[str]:
    from backend.graph.finora_graph import graph

    # Resolve yf_ticker from universe (e.g. TCS → TCS.NS, RELIANCE → RELIANCE.NS)
    entry = universe.get_by_ticker(req.ticker) if req.ticker else None
    yf_ticker = entry.get("yf_ticker", req.ticker) if entry else req.ticker

    initial_state = {
        "query": req.query,
        "ticker": req.ticker,
        "yf_ticker": yf_ticker,
        "company_name": entry.get("name", req.ticker) if entry else req.ticker,
        "currency": entry.get("currency", "USD") if entry else "USD",
        "user_mode": req.user_mode,
        "session_id": req.session_id,
        "conversation_history": [t.model_dump() for t in req.conversation_history],
        "intents": [],
        "guardrail_flags": [],
        "guardrail_blocked": False,
        "realtime_context": None,
        "news_chunks": [],
        "historical_chunks": [],
        "filings_chunks": [],
        "financials_chunks": [],
        "fundamental_data": None,
        "sector_context": None,
        "fused_context": "",
        "response": "",
        "followup_questions": [],
        "citations": [],
        "confidence_score": 0.0,
        "disclaimer_text": "",
        "trace_id": str(uuid.uuid4())[:8],
        "retrieval_scores": {},
    }

    # Per-request unique thread_id — prevents MemorySaver from accumulating
    # operator.add fields (news_chunks, historical_chunks) across invocations.
    # Conversation history is passed explicitly in initial_state, so nothing is lost.
    trace_id = initial_state["trace_id"]
    config = {"configurable": {"thread_id": f"{req.session_id}:{req.ticker}:{trace_id}"}}

    try:
        yield _sse({"type": "status", "message": "Analyzing query..."})

        # Early cache bypass — skip entire graph if response is cached
        # Uses TTL-only check (no price data yet); price-based invalidation runs in response_node
        if req.ticker and not _resp_is_volatile(req.query):
            _key = _resp_cache_key(req.ticker, req.query, req.user_mode)
            _cached_text = _resp_get_cached(_key, current_pct=None)
            if _cached_text:
                log.info("early_cache_hit", ticker=req.ticker, session=req.session_id)
                yield _sse({"type": "guardrail", "status": "allowed"})
                yield _sse({"type": "intent", "intents": []})
                lines = _cached_text.split("\n")
                for i, line in enumerate(lines):
                    content = line + ("\n" if i < len(lines) - 1 else "")
                    yield _sse({"type": "token", "content": content})
                yield _sse({"type": "done", "trace_id": trace_id, "confidence": 0.0, "cached": True})
                return

        # Stream graph events node-by-node
        async for event in graph.astream(initial_state, config=config):
            node_name = next(iter(event))
            node_output = event[node_name]

            if node_name == "guardrail_check":
                blocked = node_output.get("guardrail_blocked", False)
                yield _sse({"type": "guardrail", "status": "blocked" if blocked else "allowed"})
                if blocked:
                    response = node_output.get("response", "")
                    disclaimer = node_output.get("disclaimer_text", "")
                    yield _sse({"type": "token", "content": response})
                    if disclaimer:
                        yield _sse({"type": "disclaimer", "text": disclaimer})
                    yield _sse({"type": "done", "trace_id": req.session_id[:8], "confidence": 0.0})
                    return

            elif node_name == "intent_classifier":
                intents = node_output.get("intents", [])
                yield _sse({"type": "intent", "intents": intents})

            elif node_name == "parallel_retrieval":
                news_n = len(node_output.get("news_chunks") or [])
                hist_n = len(node_output.get("historical_chunks") or [])
                has_rt = node_output.get("realtime_context") is not None
                yield _sse({
                    "type": "retrieving",
                    "status": "done",
                    "news_chunks": news_n,
                    "historical_chunks": hist_n,
                    "realtime": has_rt,
                })

            elif node_name == "response_node":
                response = node_output.get("response", "")
                # Stream line-by-line — preserves markdown structure (## headers, bullets)
                lines = response.split("\n")
                for i, line in enumerate(lines):
                    content = line + ("\n" if i < len(lines) - 1 else "")
                    yield _sse({"type": "token", "content": content})
                # Follow-up suggestions
                suggestions = node_output.get("followup_questions") or []
                if suggestions:
                    yield _sse({"type": "suggestions", "questions": suggestions})

        # Final state — emit citations, disclaimer, done
        final = await graph.aget_state(config)
        final_vals = final.values if final else {}

        # Shared intent + keyword context for gating visual/news output
        _active_intents = set(final_vals.get("intents") or [])
        _query_words = set(req.query.lower().split())

        _news_intents = {"news"}
        _news_keywords = {"news", "why", "drop", "rise", "fell", "rally", "crash", "surge",
                          "spike", "decline", "moved", "sliding", "today", "week", "recent",
                          "latest", "reported", "announced", "earnings", "results", "catalyst"}
        _should_cite = bool(
            _active_intents & _news_intents
            or _query_words & _news_keywords
        )

        citations = final_vals.get("citations", [])
        if citations and _should_cite:
            yield _sse({"type": "citation", "sources": citations})

        disclaimer = final_vals.get("disclaimer_text", "")
        if disclaimer:
            yield _sse({"type": "disclaimer", "text": disclaimer})

        # Price chart — line chart for price/movement queries only
        # Suppressed for single-fact questions (P/E, price, margin, "should I invest", etc.)
        _SINGLE_FACT_STARTERS = ("what is", "what's", "what are", "how much", "give me the",
                                  "tell me the", "should i", "is it", "is this", "am i")
        _ql = req.query.lower().strip()
        _is_single_fact = (
            len(req.query.split()) <= 12
            and any(_ql.startswith(p) for p in _SINGLE_FACT_STARTERS)
        )
        _chart_intents = {"real_time", "historical"}
        _chart_keywords = {"chart", "price", "movement", "trend", "performance", "summarize",
                           "visualize", "graph", "drop", "rise", "fell", "rally", "crash",
                           "surge", "spike", "decline", "week", "month", "year", "today",
                           "yesterday", "52", "high", "low", "range", "how has", "how did",
                           "historical", "overview", "analyse", "analyze", "tell me about"}
        _should_chart = not _is_single_fact and bool(
            _active_intents & _chart_intents
            or _query_words & _chart_keywords
        )
        if yf_ticker and _should_chart:
            try:
                import asyncio as _asyncio
                from backend.rag.yahoo_client import fetch_ohlcv as _fetch_ohlcv
                currency = initial_state.get("currency", "USD")

                range_str, interval, label = _parse_chart_timeframe(req.query)

                def _get_bars():
                    df = _fetch_ohlcv(yf_ticker, range_str=range_str, interval=interval)
                    if df.empty:
                        return []
                    bars = []
                    for dt, row in df.iterrows():
                        try:
                            date_str = str(dt) if interval in ("5m", "30m") else str(dt.date())
                            bars.append({
                                "date": date_str,
                                "open": round(float(row["Open"]), 4),
                                "high": round(float(row["High"]), 4),
                                "low": round(float(row["Low"]), 4),
                                "close": round(float(row["Close"]), 4),
                            })
                        except Exception:
                            continue
                    return bars

                loop = _asyncio.get_event_loop()
                bars = await loop.run_in_executor(None, _get_bars)
                if bars:
                    yield _sse({
                        "type": "chart_data",
                        "ticker": req.ticker,
                        "currency": currency,
                        "label": label,
                        "bars": bars,
                    })
            except Exception as chart_exc:
                log.debug("chart_data_fetch_failed", error=str(chart_exc))

        # Finance bar chart — only for multi-year financial comparisons or full summaries
        # NOT for single-metric, opinion, news, or short factual questions
        _SUMMARY_TRIGGERS = frozenset({
            "summarize", "summary", "overview", "analyse", "analyze",
            "tell me about", "breakdown", "what do you think", "how is", "how's",
        })
        _FINANCE_HISTORY_TRIGGERS = frozenset({
            "revenue", "income", "profit", "earnings history", "annual revenue",
            "annual income", "annual profit", "fiscal year", "financial performance",
            "financial history", "balance sheet", "cash flow", "how has", "how did",
            "over the years", "growth rate", "projected growth", "financial trend",
        })
        _is_summary = any(w in _ql for w in _SUMMARY_TRIGGERS)
        _is_finance_history = any(w in _ql for w in _FINANCE_HISTORY_TRIGGERS)
        _should_finance_chart = (_is_summary or _is_finance_history) and not _is_single_fact
        if _should_finance_chart:
            _fd = final_vals.get("fundamental_data") or {}
            _income = _fd.get("annual_income") or []
            if len(_income) >= 2:
                currency = initial_state.get("currency", "USD")
                _bars = []
                for r in reversed(_income[:5]):
                    period = r.get("period", "")
                    fy = f"FY{period[:4]}" if period else "?"
                    rev = r.get("revenue")
                    ni = r.get("net_income")
                    if rev is not None:
                        _bars.append({
                            "period": fy,
                            "revenue": round(rev / 1e9, 1),
                            "net_income": round(ni / 1e9, 1) if ni is not None else None,
                        })
                if _bars:
                    yield _sse({
                        "type": "finance_chart",
                        "ticker": req.ticker,
                        "currency": currency,
                        "bars": _bars,
                    })

        confidence = final_vals.get("confidence_score", 0.0)
        trace_id = final_vals.get("trace_id", req.session_id[:8])
        from backend.observability.langsmith_url import get_project_url
        langsmith_url = get_project_url()
        yield _sse({
            "type": "done",
            "trace_id": trace_id,
            "confidence": confidence,
            "langsmith_url": langsmith_url,
        })

    except Exception as exc:
        log.error("graph_stream_failed", session=req.session_id, error=str(exc))
        yield _sse({"type": "error", "message": "An error occurred processing your query."})
        yield _sse({"type": "done", "trace_id": req.session_id[:8], "confidence": 0.0})


@router.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, body: ChatRequest) -> StreamingResponse:
    if len(body.conversation_history) > MAX_CONVERSATION_TURNS:
        body.conversation_history = body.conversation_history[-MAX_CONVERSATION_TURNS:]

    log.info("chat_request", session=body.session_id, ticker=body.ticker, query_len=len(body.query))

    return StreamingResponse(
        _stream_graph(body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
