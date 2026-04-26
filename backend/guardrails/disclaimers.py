from __future__ import annotations

_DISCLAIMERS = {
    "IN": (
        "⚠ For informational purposes only. Not financial advice. "
        "Consult a SEBI-registered investment advisor before making decisions."
    ),
    "US": (
        "⚠ For informational purposes only. Not financial advice per SEC rules. "
        "Consult a registered investment advisor."
    ),
    "GLOBAL": (
        "⚠ Informational only. Not investment advice. "
        "Past performance does not guarantee future results."
    ),
}


def get_disclaimer(locale: str = "IN") -> str:
    return _DISCLAIMERS.get(locale.upper(), _DISCLAIMERS["GLOBAL"])
