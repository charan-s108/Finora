#!/usr/bin/env python3
"""
Fetch S&P 500 + NIFTY 50 tickers and write data/universe/stocks.json.
Run once before starting the backend:
    python backend/scripts/build_universe.py
"""

import io
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUTPUT = ROOT / "backend" / "data" / "universe" / "stocks.json"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _html_tables(url: str) -> list:
    import pandas as pd
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    return pd.read_html(io.StringIO(resp.text), header=0)


def fetch_sp500() -> list[dict]:
    print("Fetching S&P 500 from Wikipedia...")
    tables = _html_tables("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    df = tables[0]

    stocks = []
    for _, row in df.iterrows():
        ticker = str(row.get("Symbol", row.get("Ticker symbol", ""))).strip().replace(".", "-")
        name = str(row.get("Security", row.get("Company", ""))).strip()
        sector = str(row.get("GICS Sector", row.get("Sector", ""))).strip()
        if not ticker or not name:
            continue
        stocks.append({
            "ticker": ticker,
            "yf_ticker": ticker,
            "name": name,
            "exchange": "NYSE/NASDAQ",
            "sector": sector,
            "country": "US",
            "currency": "USD",
        })

    print(f"  S&P 500: {len(stocks)} stocks")
    return stocks


def fetch_nifty50() -> list[dict]:
    print("Fetching NIFTY 50 from Wikipedia...")
    tables = _html_tables("https://en.wikipedia.org/wiki/NIFTY_50")

    df = None
    for t in tables:
        cols = [str(c).lower() for c in t.columns]
        if any("symbol" in c or "ticker" in c for c in cols):
            df = t
            break

    if df is None:
        raise RuntimeError("No NIFTY 50 table found on Wikipedia")

    col_map = {str(c).lower(): c for c in df.columns}
    sym_col = next((col_map[c] for c in col_map if "symbol" in c or "ticker" in c), None)
    name_col = next((col_map[c] for c in col_map if "company" in c or "name" in c or "stock" in c), None)
    sect_col = next((col_map[c] for c in col_map if "sector" in c or "industry" in c), None)

    if sym_col is None or name_col is None:
        raise RuntimeError("NIFTY 50 table missing required columns")

    stocks = []
    for _, row in df.iterrows():
        ticker = str(row[sym_col]).strip()
        name = str(row[name_col]).strip()
        sector = str(row[sect_col]).strip() if sect_col else ""
        if not ticker or ticker.lower() == "nan":
            continue
        stocks.append({
            "ticker": ticker,
            "yf_ticker": f"{ticker}.NS",
            "name": name,
            "exchange": "NSE",
            "sector": sector,
            "country": "IN",
            "currency": "INR",
        })

    print(f"  NIFTY 50: {len(stocks)} stocks")
    return stocks
    

def build() -> None:
    sp500 = fetch_sp500()
    time.sleep(1)
    nifty50 = fetch_nifty50()

    # Deduplicate by yf_ticker
    seen: set[str] = set()
    all_stocks: list[dict] = []
    for s in sp500 + nifty50:
        key = s["yf_ticker"].upper()
        if key not in seen:
            seen.add(key)
            all_stocks.append(s)

    print(f"\nTotal universe: {len(all_stocks)} stocks")
    OUTPUT.write_text(json.dumps(all_stocks, indent=2, ensure_ascii=False))
    print(f"Written → {OUTPUT}")


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
