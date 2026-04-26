"""
Financial guardrails FastAPI middleware — request-level content policy enforcement.

Runs before the route handler to reject clearly non-financial queries
without spending Groq tokens on the graph-level classifier.
"""
from __future__ import annotations

import re

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

_HARD_BLOCK_PATTERNS = [
    re.compile(r"\b(hack|exploit|malware|phishing|ransomware)\b", re.I),
    re.compile(r"\b(credit card number|cvv|ssn|social security)\b", re.I),
]

_CHAT_PATH = "/api/chat"


class FinancialGuardrailMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path == _CHAT_PATH:
            try:
                body = await request.json()
                query = body.get("query", "")
                for pattern in _HARD_BLOCK_PATTERNS:
                    if pattern.search(query):
                        return JSONResponse(
                            status_code=400,
                            content={"detail": "Query violates content policy."},
                        )
            except Exception:
                pass  # malformed JSON handled downstream

        return await call_next(request)
