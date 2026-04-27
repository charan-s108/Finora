from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

import numpy as np
import pandas as pd

EventType = Literal["earnings_week", "macro_shock", "sector_rotation", "fed_meeting", "unusual_volume"]


@dataclass
class FinancialChunk:
    text: str           # embeddable summary_text
    metadata: dict[str, Any] = field(default_factory=dict)


class FinancialEventChunker:
    """
    Detects significant events in OHLCV data and creates 5-trading-day windows around each.
    Each chunk is embedded via its LLM-generated summary_text.
    """

    VOLUME_Z_THRESHOLD = 2.0
    RETURN_THRESHOLD = 0.03     # 3% single-day move
    WINDOW_DAYS = 5             # days before+after event

    def chunk(self, df: pd.DataFrame, ticker: str) -> list[FinancialChunk]:
        """
        df: DataFrame with DatetimeIndex, columns [Open, High, Low, Close, Volume].
        Returns FinancialChunk list, one per detected event window.
        """
        if df.empty or len(df) < 20:
            return []

        df = df.copy()
        df["return_pct"] = df["Close"].pct_change()
        vol_mean = df["Volume"].rolling(30, min_periods=10).mean()
        vol_std = df["Volume"].rolling(30, min_periods=10).std().replace(0, 1)
        df["volume_z"] = (df["Volume"] - vol_mean) / vol_std

        event_indices = self._detect_events(df)
        chunks: list[FinancialChunk] = []
        seen_windows: set[int] = set()

        for idx in event_indices:
            # 5-day window: 2 before, event, 2 after
            start = max(0, idx - 2)
            end = min(len(df), idx + 3)

            # Skip if this window overlaps a seen one
            if any(i in seen_windows for i in range(start, end)):
                continue
            seen_windows.update(range(start, end))

            window = df.iloc[start:end]
            event_type = self._classify_event(df.iloc[idx])
            chunk = self._build_chunk(window, ticker, event_type, df.iloc[idx])
            chunks.append(chunk)

        return chunks

    def _detect_events(self, df: pd.DataFrame) -> list[int]:
        events: list[int] = []
        for i in range(len(df)):
            row = df.iloc[i]
            ret = abs(row.get("return_pct", 0) or 0)
            vol_z = row.get("volume_z", 0) or 0
            if (ret >= self.RETURN_THRESHOLD) or (vol_z >= self.VOLUME_Z_THRESHOLD):
                events.append(i)
        return events

    def _classify_event(self, row: pd.Series) -> EventType:
        vol_z = row.get("volume_z", 0) or 0
        ret = row.get("return_pct", 0) or 0
        if vol_z >= 3.0 and abs(ret) >= 0.05:
            return "earnings_week"
        if abs(ret) >= 0.05:
            return "macro_shock"
        if vol_z >= self.VOLUME_Z_THRESHOLD:
            return "unusual_volume"
        return "sector_rotation"

    def _build_chunk(
        self,
        window: pd.DataFrame,
        ticker: str,
        event_type: EventType,
        event_row: pd.Series,
    ) -> FinancialChunk:
        start_date = str(window.index[0].date()) if hasattr(window.index[0], "date") else str(window.index[0])
        end_date = str(window.index[-1].date()) if hasattr(window.index[-1], "date") else str(window.index[-1])

        ret_pct = float(event_row.get("return_pct", 0) or 0) * 100
        vol_z = float(event_row.get("volume_z", 0) or 0)
        close_start = float(window["Close"].iloc[0])
        close_end = float(window["Close"].iloc[-1])
        window_return = (close_end - close_start) / close_start * 100 if close_start else 0

        summary = (
            f"{ticker} experienced a {event_type.replace('_', ' ')} event from {start_date} to {end_date}. "
            f"On the event day, the stock moved {ret_pct:+.2f}% with volume {vol_z:+.1f}x the 30-day average. "
            f"Over the 5-day window, {ticker} returned {window_return:+.2f}% "
            f"(from ${close_start:.2f} to ${close_end:.2f})."
        )

        return FinancialChunk(
            text=summary,
            metadata={
                "ticker": ticker,
                "event_type": event_type,
                "date_range": f"{start_date}:{end_date}",
                "start_date": start_date,
                "end_date": end_date,
                "return_pct": round(ret_pct, 4),
                "volume_z_score": round(vol_z, 4),
                "window_return_pct": round(window_return, 4),
                "open": round(float(window["Open"].iloc[0]), 4),
                "high": round(float(window["High"].max()), 4),
                "low": round(float(window["Low"].min()), 4),
                "close": round(float(window["Close"].iloc[-1]), 4),
                "volume": int(window["Volume"].sum()),
            },
        )
