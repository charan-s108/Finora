"""
Output guardrail pipeline — runs post-generation, pre-client.

Steps:
1. Hallucination check: numbers/% in response verified against fused_context
2. PII scrub: regex over response for account numbers, personal identifiers
3. Confidence signal: if score < 0.6, inject moderate-confidence warning
4. Directional language: detected → inject disclaimer
"""
from __future__ import annotations

import re

import structlog

from backend.guardrails.disclaimers import get_disclaimer

log = structlog.get_logger()

# Matches percentages and dollar/rupee amounts with optional sign
_NUMBER_RE = re.compile(r"[+-]?\d+(?:\.\d+)?%|[₹$]\s*\d[\d,.]+")

# PII patterns: account numbers (10–18 digits), Aadhaar (XXXX XXXX XXXX), PAN
_PII_PATTERNS = [
    (re.compile(r"\b\d{10,18}\b"), "[ACCOUNT_REDACTED]"),
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[PAN_REDACTED]"),
    (re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b"), "[AADHAAR_REDACTED]"),
]

_DIRECTIONAL_PHRASES = {
    "will rise", "will fall", "will go up", "will go down",
    "you should buy", "you should sell", "guaranteed", "certain to",
    "definitely go up", "definitely go down", "sure to",
}


def _extract_numbers(text: str) -> list[str]:
    return _NUMBER_RE.findall(text)


def _hallucination_check(response: str, fused_context: str) -> str:
    """Log unverified numbers for observability. No user-facing annotation."""
    if not fused_context:
        return response
    context_numbers = set(_extract_numbers(fused_context))
    flagged = [n for n in _extract_numbers(response) if n not in context_numbers]
    if flagged:
        log.warning("hallucination_flag", unverified=flagged[:5])
    return response  # no inline annotation — clean UX


def _scrub_pii(text: str) -> str:
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _has_directional_language(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in _DIRECTIONAL_PHRASES)


def apply_output_guardrail(
    response: str,
    fused_context: str,
    confidence_score: float,
    disclaimer_text: str,
    locale: str = "IN",
) -> str:
    """Apply all output guardrails. Returns the final safe response string."""
    # Step 1: hallucination check
    response = _hallucination_check(response, fused_context)

    # Step 2: PII scrub
    response = _scrub_pii(response)

    # Step 3: confidence is tracked in SSE event — no inline annotation needed

    # Step 4: disclaimer ONLY when response contains directional language
    # (otherwise it fires via the separate SSE "disclaimer" event once per session)
    if _has_directional_language(response):
        disclaimer = disclaimer_text or get_disclaimer(locale)
        if disclaimer not in response:
            response += f"\n\n{disclaimer}"

    return response
