"""
Finora FastMCP server — stdio transport.

Run from repo root:
    cd backend && python -m finora_mcp.server

Tools exposed:
    get_realtime_quote, search_historical_rag, search_news_rag,
    get_fundamentals, screen_stocks, get_stock_universe
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"

sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from fastmcp import FastMCP

from finora_mcp.tools.fundamentals import get_fundamentals
from finora_mcp.tools.historical import search_historical_rag
from finora_mcp.tools.news import search_news_rag
from finora_mcp.tools.quote import get_realtime_quote
from finora_mcp.tools.screener import get_stock_universe, screen_stocks

mcp = FastMCP("finora-mcp")

mcp.tool()(get_realtime_quote)
mcp.tool()(search_historical_rag)
mcp.tool()(search_news_rag)
mcp.tool()(get_fundamentals)
mcp.tool()(screen_stocks)
mcp.tool()(get_stock_universe)


if __name__ == "__main__":
    mcp.run(transport="stdio")
