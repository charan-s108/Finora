#!/usr/bin/env python3
"""
Seed 20yr OHLCV data into Qdrant (finora_historical collection).

Usage:
    python backend/scripts/ingest_historical.py --tickers AAPL MSFT NVDA RELIANCE.NS --years 20
    python backend/scripts/ingest_historical.py --all --years 20
    python backend/scripts/ingest_historical.py --tickers AAPL --years 5
    python backend/scripts/ingest_historical.py --tickers ZBRA ZBH ZTS --years 5 (For Test Purpose Only!)
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from backend.rag.ingestion.collections import ensure_collections, get_client
from backend.rag.ingestion.historical import ingest_ticker, ingest_universe

UNIVERSE_PATH = ROOT / "backend" / "data" / "universe" / "stocks.json"

def load_universe() -> list[dict]:
    if not UNIVERSE_PATH.exists():
        print(f"ERROR: Universe not found at {UNIVERSE_PATH}. Run build_universe.py first.")
        sys.exit(1)
    with open(UNIVERSE_PATH) as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest historical OHLCV into Qdrant")
    parser.add_argument("--tickers", nargs="+", help="Tickers to ingest (e.g. AAPL MSFT RELIANCE.NS)")
    parser.add_argument("--all", action="store_true", help="Ingest full universe (~553 tickers)")
    parser.add_argument("--years", type=int, default=20, help="Years of history (default: 20)")
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds between tickers (default: 3)")
    args = parser.parse_args()

    if not args.tickers and not args.all:
        parser.print_help()
        sys.exit(1)

    client = get_client()
    print("Connected to Qdrant.")
    ensure_collections(client)
    print("Collections ready.")

    universe = load_universe()
    ticker_map = {s["ticker"].upper(): s for s in universe}
    ticker_map.update({s.get("yf_ticker", "").upper(): s for s in universe})

    stocks = universe if args.all else [
        ticker_map.get(t.upper(), {"ticker": t, "yf_ticker": t, "name": t})
        for t in (args.tickers or [])
    ]

    print(f"\nIngesting {len(stocks)} ticker(s) — {args.years}yr history...\n")

    if len(stocks) == 1:
        s = stocks[0]
        n = ingest_ticker(s["ticker"], s.get("yf_ticker", s["ticker"]), args.years, client)
        print(f"{s['ticker']}: {n} chunks")
    else:
        results = ingest_universe(stocks, years=args.years, delay_seconds=args.delay)
        total = sum(results.values())
        success = sum(1 for v in results.values() if v > 0)
        print(f"\nDone: {success}/{len(stocks)} tickers, {total} total chunks")
        failures = [t for t, v in results.items() if v == 0]
        if failures:
            print(f"Zero chunks (failed/delisted): {failures[:20]}")


if __name__ == "__main__":
    main()
