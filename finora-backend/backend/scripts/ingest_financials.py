#!/usr/bin/env python3
"""
Pre-ingest financial statements (Income, Balance Sheet, Cash Flow) for all stocks
into Qdrant finora_financials collection.

Run once, then refresh quarterly to keep data current.

Usage:
    python backend/scripts/ingest_financials.py --all
    python backend/scripts/ingest_financials.py --tickers AAPL MSFT HDFCBANK TCS
    python backend/scripts/ingest_financials.py --limit 50
    python backend/scripts/ingest_financials.py --all --skip-existing
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

from backend.rag.ingestion.collections import ensure_collections, get_client, collection_name
from backend.rag.ingestion.financials import ingest_ticker

UNIVERSE_PATH = ROOT / "backend" / "data" / "universe" / "stocks.json"


def load_universe() -> list[dict]:
    if not UNIVERSE_PATH.exists():
        print(f"ERROR: Universe not found at {UNIVERSE_PATH}. Run build_universe.py first.")
        sys.exit(1)
    with open(UNIVERSE_PATH) as f:
        return json.load(f)


def _already_indexed(client, col: str, ticker: str) -> bool:
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        result = client.scroll(
            collection_name=col,
            scroll_filter=Filter(must=[FieldCondition(key="ticker", match=MatchValue(value=ticker))]),
            limit=1,
            with_payload=False,
            with_vectors=False,
        )
        return len(result[0]) > 0
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest financial statements into Qdrant finora_financials"
    )
    parser.add_argument("--tickers", nargs="+", help="Specific tickers to ingest")
    parser.add_argument("--all", action="store_true", help="Ingest full universe (~555 tickers)")
    parser.add_argument("--limit", type=int, help="Ingest only first N stocks from universe")
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds between tickers (default: 1.5)")
    parser.add_argument("--skip-existing", action="store_true", help="Skip tickers already in Qdrant")
    args = parser.parse_args()

    if not args.tickers and not args.all and not args.limit:
        parser.print_help()
        sys.exit(1)

    client = get_client()
    print("Connected to Qdrant.")
    ensure_collections(client)
    print("Collections ready.")

    universe = load_universe()
    ticker_map = {s["ticker"].upper(): s for s in universe}
    ticker_map.update({s.get("yf_ticker", "").upper(): s for s in universe if s.get("yf_ticker")})

    if args.all or args.limit:
        stocks = universe[:args.limit] if args.limit else universe
    else:
        stocks = [
            ticker_map.get(t.upper(), {"ticker": t, "yf_ticker": t, "currency": "USD"})
            for t in (args.tickers or [])
        ]

    col = collection_name("financials")
    total = len(stocks)
    done = 0
    skipped = 0
    total_chunks = 0

    print(f"\nIngesting {total} tickers into {col}...\n")

    for i, stock in enumerate(stocks, 1):
        ticker = stock.get("ticker", "")
        yf_ticker = stock.get("yf_ticker", ticker)
        currency = stock.get("currency", "USD")

        if args.skip_existing and _already_indexed(client, col, ticker):
            print(f"[{i:4d}/{total}] SKIP  {ticker:12s} (already indexed)")
            skipped += 1
            continue

        try:
            chunks = ingest_ticker(
                ticker=ticker,
                yf_ticker=yf_ticker,
                currency=currency,
                client=client,
            )
            total_chunks += chunks
            done += 1
            status = f"{chunks:3d} chunks" if chunks else "no data"
            print(f"[{i:4d}/{total}] OK    {ticker:12s}  {status}")
        except Exception as exc:
            print(f"[{i:4d}/{total}] FAIL  {ticker:12s}  {exc}")

        if i < total:
            time.sleep(args.delay)

    print(f"\n{'─' * 50}")
    print(f"Done. {done} ingested, {skipped} skipped, {total_chunks} total chunks.")
    print(f"Collection: {col}")


if __name__ == "__main__":
    main()
