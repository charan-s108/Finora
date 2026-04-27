"""Prometheus metrics — optional, enabled via METRICS_ENABLED=true."""
from __future__ import annotations

import os

_ENABLED = os.getenv("METRICS_ENABLED", "false").lower() == "true"

if _ENABLED:
    try:
        from prometheus_client import Counter, Histogram, start_http_server

        chat_requests_total = Counter("finora_chat_requests_total", "Total chat requests")
        chat_latency_seconds = Histogram("finora_chat_latency_seconds", "Chat end-to-end latency")
        retrieval_chunks = Histogram(
            "finora_retrieval_chunks", "Chunks retrieved per branch",
            labelnames=["branch"],
        )
        guardrail_blocks_total = Counter("finora_guardrail_blocks_total", "Guardrail blocked requests")

        def start_metrics_server(port: int = 9090) -> None:
            start_http_server(port)
    except ImportError:
        pass
