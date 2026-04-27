#!/usr/bin/env python3
"""
Fetch S&P 500 + NIFTY 50 tickers and write data/universe/stocks.json.
Run once before starting the backend:
    python scripts/build_universe.py
"""

import io
import json
import sys
import time
from pathlib import Path

import requests

# backend/data/universe/stocks.json — committed to git, baked into Docker image
OUTPUT = Path(__file__).parent.parent / "data" / "universe" / "stocks.json"
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
    url = "https://en.wikipedia.org/wiki/NIFTY_50"
    try:
        tables = _html_tables(url)
        # Find the table that has a ticker/symbol column
        df = None
        for t in tables:
            cols = [str(c).lower() for c in t.columns]
            if any("symbol" in c or "ticker" in c for c in cols):
                df = t
                break
        if df is None:
            raise ValueError("No NIFTY 50 table found")

        col_map = {str(c).lower(): c for c in df.columns}
        sym_col = next((col_map[c] for c in col_map if "symbol" in c or "ticker" in c), None)
        name_col = next((col_map[c] for c in col_map if "company" in c or "name" in c or "stock" in c), None)
        sect_col = next((col_map[c] for c in col_map if "sector" in c or "industry" in c), None)

        stocks = []
        for _, row in df.iterrows():
            ticker = str(row[sym_col]).strip() if sym_col else ""
            name = str(row[name_col]).strip() if name_col else ticker
            sector = str(row[sect_col]).strip() if sect_col else ""
            if not ticker or ticker == "nan":
                continue
            yf_ticker = f"{ticker}.NS"
            stocks.append({
                "ticker": ticker,
                "yf_ticker": yf_ticker,
                "name": name,
                "exchange": "NSE",
                "sector": sector,
                "country": "IN",
                "currency": "INR",
            })

        print(f"  NIFTY 50: {len(stocks)} stocks")
        return stocks

    except Exception as exc:
        print(f"  WARNING: NIFTY 50 fetch failed ({exc}), using hardcoded fallback")
        return _nifty50_fallback()


def _nifty50_fallback() -> list[dict]:
    entries = [
        ("RELIANCE", "Reliance Industries", "Energy"),
        ("TCS", "Tata Consultancy Services", "Information Technology"),
        ("HDFCBANK", "HDFC Bank", "Financial Services"),
        ("INFY", "Infosys", "Information Technology"),
        ("HINDUNILVR", "Hindustan Unilever", "FMCG"),
        ("ICICIBANK", "ICICI Bank", "Financial Services"),
        ("KOTAKBANK", "Kotak Mahindra Bank", "Financial Services"),
        ("SBIN", "State Bank of India", "Financial Services"),
        ("BHARTIARTL", "Bharti Airtel", "Telecom"),
        ("ITC", "ITC Limited", "FMCG"),
        ("BAJFINANCE", "Bajaj Finance", "Financial Services"),
        ("LT", "Larsen & Toubro", "Construction"),
        ("HCLTECH", "HCL Technologies", "Information Technology"),
        ("ASIANPAINT", "Asian Paints", "Materials"),
        ("AXISBANK", "Axis Bank", "Financial Services"),
        ("MARUTI", "Maruti Suzuki India", "Automobile"),
        ("SUNPHARMA", "Sun Pharmaceutical", "Healthcare"),
        ("TITAN", "Titan Company", "Consumer Discretionary"),
        ("ULTRACEMCO", "UltraTech Cement", "Materials"),
        ("NESTLEIND", "Nestle India", "FMCG"),
        ("WIPRO", "Wipro", "Information Technology"),
        ("ADANIENT", "Adani Enterprises", "Industrials"),
        ("ADANIPORTS", "Adani Ports & SEZ", "Industrials"),
        ("BAJAJFINSV", "Bajaj Finserv", "Financial Services"),
        ("BPCL", "Bharat Petroleum", "Energy"),
        ("CIPLA", "Cipla", "Healthcare"),
        ("COALINDIA", "Coal India", "Energy"),
        ("DIVISLAB", "Divi's Laboratories", "Healthcare"),
        ("DRREDDY", "Dr. Reddy's Laboratories", "Healthcare"),
        ("EICHERMOT", "Eicher Motors", "Automobile"),
        ("GRASIM", "Grasim Industries", "Materials"),
        ("HDFCLIFE", "HDFC Life Insurance", "Financial Services"),
        ("HEROMOTOCO", "Hero MotoCorp", "Automobile"),
        ("HINDALCO", "Hindalco Industries", "Materials"),
        ("INDUSINDBK", "IndusInd Bank", "Financial Services"),
        ("JSWSTEEL", "JSW Steel", "Materials"),
        ("M&M", "Mahindra & Mahindra", "Automobile"),
        ("NTPC", "NTPC", "Utilities"),
        ("ONGC", "Oil & Natural Gas Corporation", "Energy"),
        ("POWERGRID", "Power Grid Corporation", "Utilities"),
        ("SBILIFE", "SBI Life Insurance", "Financial Services"),
        ("SHREECEM", "Shree Cement", "Materials"),
        ("TATACONSUM", "Tata Consumer Products", "FMCG"),
        ("TATAMOTORS", "Tata Motors", "Automobile"),
        ("TATASTEEL", "Tata Steel", "Materials"),
        ("TECHM", "Tech Mahindra", "Information Technology"),
        ("TRENT", "Trent", "Consumer Discretionary"),
        ("UPL", "UPL", "Materials"),
        ("VEDL", "Vedanta", "Materials"),
        ("ZOMATO", "Zomato", "Consumer Discretionary"),
    ]
    return [
        {
            "ticker": t,
            "yf_ticker": f"{t}.NS",
            "name": n,
            "exchange": "NSE",
            "sector": s,
            "country": "IN",
            "currency": "INR",
        }
        for t, n, s in entries
    ]


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
