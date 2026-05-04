"""
Finora LangGraph StateGraph.

Topology:
  guardrail_check → [blocked → END | allowed → intent_classifier]
  intent_classifier → parallel_retrieval (asyncio.gather over all needed branches)
  parallel_retrieval → fusion_node → response_node → END

Note: parallel_retrieval is a single async node that fans out internally via
asyncio.gather — simpler and more reliable than graph-level fan-out for this use case.
"""
from __future__ import annotations

import asyncio

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from backend.graph.nodes.fusion_node import fusion_node
from backend.graph.nodes.fundamentals_node import fundamentals_node
from backend.graph.nodes.historical_rag_node import historical_rag_node
from backend.graph.nodes.intent_classifier import intent_classifier_node
from backend.graph.nodes.filings_rag_node import filings_rag_node
from backend.graph.nodes.financials_rag_node import financials_rag_node
from backend.graph.nodes.news_rag_node import news_rag_node
from backend.graph.nodes.realtime_node import realtime_node
from backend.graph.nodes.response_node import response_node
from backend.graph.state import FiNoraState
from backend.guardrails.classifier import guardrail_check_node, route_after_guardrail

log = structlog.get_logger()


async def parallel_retrieval_node(state: FiNoraState) -> dict:
    """
    Fan-out: runs all applicable retrieval branches concurrently via asyncio.gather.
    Merges results back into state.
    """
    tasks = [
        realtime_node(state),
        news_rag_node(state),
        historical_rag_node(state),
        fundamentals_node(state),
        filings_rag_node(state),
        financials_rag_node(state),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    merged: dict = {
        "realtime_context": None,
        "news_chunks": [],
        "historical_chunks": [],
        "filings_chunks": [],
        "financials_chunks": [],
        "fundamental_data": None,
        "sector_context": None,
        "retrieval_scores": {},
    }
    for r in results:
        if isinstance(r, Exception):
            log.error("parallel_retrieval_branch_failed", error=str(r))
            continue
        for key, val in r.items():
            if key in ("news_chunks", "historical_chunks", "filings_chunks", "financials_chunks"):
                merged[key] = merged.get(key, []) + (val or [])
            elif key == "retrieval_scores":
                merged["retrieval_scores"].update(val or {})
            elif val is not None:
                merged[key] = val

    return merged


def _build_graph() -> StateGraph:
    builder = StateGraph(FiNoraState)

    builder.add_node("guardrail_check", guardrail_check_node)
    builder.add_node("intent_classifier", intent_classifier_node)
    builder.add_node("parallel_retrieval", parallel_retrieval_node)
    builder.add_node("fusion_node", fusion_node)
    builder.add_node("response_node", response_node)

    builder.set_entry_point("guardrail_check")

    builder.add_conditional_edges(
        "guardrail_check",
        route_after_guardrail,
        {"blocked": END, "allowed": "intent_classifier"},
    )

    builder.add_edge("intent_classifier", "parallel_retrieval")
    builder.add_edge("parallel_retrieval", "fusion_node")
    builder.add_edge("fusion_node", "response_node")
    builder.add_edge("response_node", END)

    return builder


# Compiled graph — shared across all requests
_checkpointer = MemorySaver()
graph = _build_graph().compile(checkpointer=_checkpointer)
