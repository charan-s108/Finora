"""
LangSmith tracing wrapper for all LangGraph runs.

LangSmith auto-instruments via environment variables when:
    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY=ls__...
    LANGCHAIN_PROJECT=finora-prod

This module provides explicit trace helpers for non-graph code paths
(MCP tools, batch ingestion, eval) that don't run through LangGraph.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Generator

import structlog

log = structlog.get_logger()

_TRACING_ENABLED = (
    os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    and bool(os.getenv("LANGCHAIN_API_KEY"))
)


@contextmanager
def trace_run(
    name: str,
    run_type: str = "chain",
    metadata: dict[str, Any] | None = None,
) -> Generator[Any, None, None]:
    """Context manager that wraps a code block in a LangSmith trace span."""
    if not _TRACING_ENABLED:
        yield None
        return

    try:
        from langsmith import trace as ls_trace

        with ls_trace(name=name, run_type=run_type, metadata=metadata or {}) as run:
            yield run
    except ImportError:
        yield None
    except Exception as exc:
        log.warning("langsmith_trace_failed", name=name, error=str(exc))
        yield None


def log_retrieval_scores(run_id: str, scores: dict[str, float]) -> None:
    """Attach retrieval scores as feedback to a LangSmith run."""
    if not _TRACING_ENABLED or not scores:
        return
    try:
        from langsmith import Client as LSClient

        client = LSClient()
        for key, value in scores.items():
            client.create_feedback(
                run_id=run_id,
                key=key,
                score=value,
            )
    except Exception as exc:
        log.warning("langsmith_feedback_failed", error=str(exc))
