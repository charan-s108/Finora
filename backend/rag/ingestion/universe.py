import json
import os
from pathlib import Path
from typing import Any

import structlog
from rapidfuzz import fuzz, process

log = structlog.get_logger()

# parents[2] = backend/ (works for both local dev and Docker: /app/data/universe/)
_UNIVERSE_PATH = Path(__file__).parents[2] / "data" / "universe" / "stocks.json"


class StockUniverse:
    def __init__(self) -> None:
        self.stocks: list[dict[str, Any]] = []
        self._search_strings: list[str] = []
        self._load()

    def _load(self) -> None:
        if not _UNIVERSE_PATH.exists():
            log.warning("universe_not_found", path=str(_UNIVERSE_PATH))
            return
        with open(_UNIVERSE_PATH) as f:
            self.stocks = json.load(f)
        # Pre-build search strings: "AAPL Apple Inc Technology US"
        self._search_strings = [
            f"{s['ticker']} {s['name']} {s.get('sector', '')} {s.get('country', '')}"
            for s in self.stocks
        ]
        log.info("universe_loaded", count=len(self.stocks))

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        if not query or not self.stocks:
            return self.stocks[:limit]

        q = query.strip()
        q_up = q.upper()
        q_low = q.lower()
        scored: list[tuple[float, int]] = []

        for i, stock in enumerate(self.stocks):
            ticker = stock["ticker"].upper()
            name_low = stock["name"].lower()

            if ticker == q_up:
                score = 200.0
            elif ticker.startswith(q_up) and len(q_up) >= 2:
                score = 170.0 + len(q_up)
            else:
                # ratio for ticker: avoids single-char 100% partial traps
                ticker_score = fuzz.ratio(q_up, ticker) * 1.2
                # partial_ratio for name: finds query as substring
                name_score = fuzz.partial_ratio(q_low, name_low)
                score = max(ticker_score, name_score)
                if score < 50:
                    continue

            scored.append((score, i))

        scored.sort(key=lambda x: -x[0])
        return [self.stocks[i] for _, i in scored[:limit]]

    def get_by_ticker(self, ticker: str) -> dict[str, Any] | None:
        ticker_upper = ticker.upper()
        for s in self.stocks:
            if s["ticker"].upper() == ticker_upper or s.get("yf_ticker", "").upper() == ticker_upper:
                return s
        return None

    def reload(self) -> None:
        self._load()


universe = StockUniverse()
