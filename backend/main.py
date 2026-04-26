import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.middleware.guardrails import FinancialGuardrailMiddleware
from api.middleware.rate_limit import limiter
from api.routes import chat, health, stocks
from rag.ingestion.universe import universe

# Loads backend/.env — Railway injects OS-level vars so this is a no-op in production
load_dotenv(Path(__file__).parent / ".env")

log = structlog.get_logger()


def _warm_yahoo_session() -> None:
    """Prime curl_cffi session cookies + crumb before first real request."""
    try:
        from rag.yahoo_client import _warm_session, _get_crumb
        _warm_session("AAPL")
        _warm_session("AAPL")  # second hit ensures cookies are set
        crumb = _get_crumb()
        log.info("yahoo_session_warmed", crumb_ok=bool(crumb))
    except Exception as exc:
        log.warning("yahoo_warm_failed", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", universe_size=len(universe.stocks))

    # Ensure data directories exist
    from pathlib import Path
    Path("data/eval_results").mkdir(parents=True, exist_ok=True)

    # Warm Yahoo Finance session so first real stock request doesn't get empty data
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _warm_yahoo_session)

    # Start background scheduler (news + historical incremental ingestion)
    scheduler = None
    if os.getenv("ENV", "development") == "production" or os.getenv("SCHEDULER_ENABLED", "false") == "true":
        from rag.ingestion.scheduler import start_scheduler
        scheduler = start_scheduler()

    yield

    if scheduler:
        from rag.ingestion.scheduler import stop_scheduler
        stop_scheduler()
    log.info("shutdown")


app = FastAPI(title="Finora API", version="1.0.0", lifespan=lifespan)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(FinancialGuardrailMiddleware)

app.include_router(health.router, prefix="/api")
app.include_router(stocks.router, prefix="/api/stocks")
app.include_router(chat.router, prefix="/api")

if __name__ == "__main__":
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
