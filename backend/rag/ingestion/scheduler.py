"""
APScheduler jobs: news ingestion every 15 min, historical update every 24 hr.
Integrated into FastAPI lifespan.
"""
from __future__ import annotations

import os

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

log = structlog.get_logger()

_scheduler: AsyncIOScheduler | None = None


async def _run_news_ingest() -> None:
    from rag.ingestion.universe import universe
    from rag.ingestion import news as news_ingest
    from rag.ingestion.collections import ensure_collections

    stocks = [s for s in universe.stocks][:50]  # Cap at 50 on scheduled runs
    if not stocks:
        return

    ensure_collections()
    results = news_ingest.ingest_universe(stocks, days=1)
    total = sum(results.values())
    log.info("scheduled_news_done", tickers=len(results), chunks=total)


async def _run_historical_update() -> None:
    from rag.ingestion.universe import universe
    from rag.ingestion import historical as hist_ingest
    from rag.ingestion.collections import ensure_collections

    # Daily update: only ingest recent 30 days of OHLCV
    stocks = universe.stocks
    if not stocks:
        return

    ensure_collections()
    # Use a subset to avoid overwhelming yfinance rate limits on daily runs
    priority = [s for s in stocks if s["country"] in ("US",)][:20]
    results = hist_ingest.ingest_universe(priority, years=1, max_workers=2)
    total = sum(results.values())
    log.info("scheduled_historical_done", tickers=len(results), chunks=total)


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler

    news_interval = int(os.getenv("NEWS_INGEST_INTERVAL_MINUTES", "15"))
    hist_interval = int(os.getenv("HISTORICAL_UPDATE_INTERVAL_HOURS", "24"))

    _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        _run_news_ingest,
        trigger=IntervalTrigger(minutes=news_interval),
        id="news_ingest",
        name="News RAG Ingest",
        replace_existing=True,
        misfire_grace_time=300,
    )

    _scheduler.add_job(
        _run_historical_update,
        trigger=IntervalTrigger(hours=hist_interval),
        id="historical_update",
        name="Historical OHLCV Update",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    _scheduler.start()
    log.info("scheduler_started", news_interval_min=news_interval, hist_interval_hr=hist_interval)
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("scheduler_stopped")
