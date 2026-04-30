#!/usr/bin/env python3
"""
Seed news corpus into Qdrant (finora_news collection) via NewsAPI.

Usage:
    python backend/scripts/ingest_news.py --tickers AAPL MSFT NVDA RELIANCE --days 7
    python backend/scripts/ingest_news.py --all --days 3
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
from backend.rag.ingestion.news import ingest_ticker, ingest_universe

UNIVERSE_PATH = ROOT / "backend" / "data" / "universe" / "stocks.json"

def load_universe() -> list[dict]:
    if not UNIVERSE_PATH.exists():
        print(f"ERROR: Universe not found. Run build_universe.py first.")
        sys.exit(1)
    with open(UNIVERSE_PATH) as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest news into Qdrant")
    parser.add_argument("--tickers", nargs="+", help="Tickers to ingest")
    parser.add_argument("--all", action="store_true", help="Ingest full universe (caution: 100 req/day limit)")
    parser.add_argument("--days", type=int, default=7, help="Days of news history (default: 7)")
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

    stocks = universe if args.all else [
        ticker_map.get(t.upper(), {"ticker": t, "yf_ticker": t, "name": t})
        for t in (args.tickers or [])
    ]

    # NewsAPI free tier: 100 req/day. Each ticker = 1 request.
    if len(stocks) > 90:
        print(f"WARNING: {len(stocks)} tickers requested but NewsAPI free tier = 100 req/day.")
        print("Capping at 90 to leave buffer.")
        stocks = stocks[:90]

    print(f"\nIngesting news for {len(stocks)} ticker(s) — last {args.days} day(s)...\n")

    if len(stocks) == 1:
        s = stocks[0]
        n = ingest_ticker(s["ticker"], s.get("name", s["ticker"]), days=args.days, client=client)
        print(f"{s['ticker']}: {n} chunks")
    else:
        results = ingest_universe(stocks, days=args.days)
        total = sum(results.values())
        success = sum(1 for v in results.values() if v > 0)
        print(f"\nDone: {success}/{len(stocks)} tickers, {total} total chunks")


if __name__ == "__main__":
    main()
