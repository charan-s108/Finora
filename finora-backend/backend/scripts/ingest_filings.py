#!/usr/bin/env python3
"""
Seed US SEC filings (10-K, 10-Q) into Qdrant (finora_filings collection).

Usage:
    python backend/scripts/ingest_filings.py --tickers AAPL MSFT NVDA
    python backend/scripts/ingest_filings.py --all
    python backend/scripts/ingest_filings.py --limit 20
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from backend.rag.ingestion.collections import ensure_collections, get_client
from backend.rag.ingestion.filings import ingest_ticker

UNIVERSE_PATH = ROOT / "backend" / "data" / "universe" / "stocks.json"

HEADERS = {
    "User-Agent": "Finora Research (finora@example.com)"
}


# ── Load universe ─────────────────────────────────────────────────────────

def load_universe():
    if not UNIVERSE_PATH.exists():
        print("ERROR: Universe missing. Run build_universe.py")
        sys.exit(1)
    return json.load(open(UNIVERSE_PATH))


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ingest SEC filings into Qdrant")
    parser.add_argument("--tickers", nargs="+")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=int, help="Limit number of tickers")
    parser.add_argument("--delay", type=float, default=1.0)

    args = parser.parse_args()

    if not args.tickers and not args.all:
        parser.print_help()
        sys.exit(1)

    client = get_client()
    ensure_collections(client)

    universe = load_universe()

    # Filter US stocks only
    us_stocks = [s for s in universe if not s["ticker"].endswith((".NS", ".BO"))]

    ticker_map = {s["ticker"].upper(): s for s in us_stocks}

    stocks = (
        us_stocks if args.all else
        [ticker_map.get(t.upper(), {"ticker": t}) for t in (args.tickers or [])]
    )

    if args.limit:
        stocks = stocks[:args.limit]

    print(f"Ingesting filings for {len(stocks)} stocks...\n")

    success = 0

    for s in stocks:
        ticker = s["ticker"]

        n = ingest_ticker(ticker, client)

        if n > 0:
            print(f"{ticker}: {n} chunks")
            success += 1
        else:
            print(f"{ticker}: no filings")

        time.sleep(args.delay)

    print(f"\nDone. Successful: {success}/{len(stocks)}")


if __name__ == "__main__":
    main()
