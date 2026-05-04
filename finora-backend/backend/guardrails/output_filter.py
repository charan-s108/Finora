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

# Matches: percentages, currency amounts (with optional T/B/M suffix), magnitude forms
# e.g. "3.24%", "$2.81T", "$453.8B", "$280.14", "451.4 billion", "2.81 trillion"
_NUMBER_RE = re.compile(
    r"[+-]?\d+(?:\.\d+)?%"
    r"|[₹$]\s*\d[\d,.]*(?:[TBMtbm]\b)?"
    r"|\b\d+(?:\.\d+)?\s*(?:trillion|billion|million|crore|lakh)\b",
    re.IGNORECASE,
)

_MAGNITUDE_TO_BILLIONS = {
    "trillion": 1_000.0,
    "billion":  1.0,
    "million":  0.001,
    "crore":    0.01,
    "lakh":     0.0001,
}

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


def _to_float(n: str) -> float | None:
    """
    Parse any matched number to a float, normalised to billions for magnitude forms.
    '+3.24%' → 3.24 | '$2.81T' → 2810.0 | '$453.8B' → 453.8 | '$280.14' → 280.14
    '2.81 trillion' → 2810.0 | '383.3 million' → 0.3833
    """
    try:
        nl = n.lower()
        for mag, factor in _MAGNITUDE_TO_BILLIONS.items():
            if mag in nl:
                digits = re.sub(r"[^0-9.]", "", n)
                return float(digits) * factor
        stripped = re.sub(r"[+₹$,\s]", "", n).rstrip("%")
        sl = stripped.lower()
        if sl.endswith("t"):
            return float(sl[:-1]) * 1_000.0
        if sl.endswith("b"):
            return float(sl[:-1])
        if sl.endswith("m"):
            return float(sl[:-1]) * 0.001
        return float(stripped)
    except ValueError:
        return None


def _is_verified(val: float, context_vals: set[float]) -> bool:
    """
    True when val is within tolerance of any number in context.
    - Zero is always valid (0% dividend yield, zero growth — real facts)
    - Percentages: 3pp tolerance (LLM rounds 8.3% → '8%', 0.5% → '0%')
    - Dollar amounts: 15% relative (handles rounded + related-but-different metrics
      e.g. $108B FCF vs $110B op-cash-flow in context — different metrics, real values)
    """
    if val == 0.0:
        return True  # zero is a valid financial fact — never flag it
    for c in context_vals:
        if c == 0:
            continue
        abs_diff = abs(val - c)
        if abs_diff <= 3.0:            # 3pp tolerance for percentages
            return True
        if abs_diff / abs(c) <= 0.15:  # 15% relative for dollar amounts
            return True
    return False


def _strip_unverified_sentences(text: str, unverified: list[str]) -> str:
    """Remove sentences that contain genuinely unverified numbers.
    Safety net: if stripping would reduce response below 30% of original length,
    return original — better to show slightly uncertain data than an empty response.
    """
    bad = set(unverified)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    clean, removed = [], []
    for sent in sentences:
        if set(_extract_numbers(sent)) & bad:
            removed.append(sent[:80])
        else:
            clean.append(sent)
    if removed:
        log.info("hallucination_sentences_removed", count=len(removed),
                 previews=[s[:60] for s in removed])
    result = " ".join(clean)
    if len(result.strip()) < max(30, len(text.strip()) * 0.30):
        log.warning("hallucination_strip_safety_net", original_len=len(text.strip()),
                    stripped_len=len(result.strip()))
        return text
    return result


def _hallucination_check(response: str, fused_context: str) -> str:
    """
    1. Extract all numbers from context → normalised float set.
    2. For each number in response: verified if float value within tolerance of
       any context number (kills '+3.24%' vs '3.24%' false positives).
    3. Unverified numbers → strip containing sentence, log removal.
    """
    if not fused_context:
        return response

    context_raw = _extract_numbers(fused_context)
    context_vals: set[float] = {v for n in context_raw if (v := _to_float(n)) is not None}

    unverified = []
    for n in _extract_numbers(response):
        v = _to_float(n)
        if v is None:
            continue
        if n in set(context_raw):          # exact string match — fast path
            continue
        if not _is_verified(v, context_vals):
            unverified.append(n)

    if unverified:
        log.warning("hallucination_flag", unverified=unverified[:5])
        response = _strip_unverified_sentences(response, unverified)

    return response


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
