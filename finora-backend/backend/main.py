import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if os.getenv("ENV", "development") != "production":
    load_dotenv(ROOT / ".env")

EVAL_DIR = ROOT / "backend" / "data" / "eval_results"
EVAL_DIR.mkdir(parents=True, exist_ok=True)

from backend.api.middleware.guardrails import FinancialGuardrailMiddleware
from backend.api.middleware.rate_limit import limiter
from backend.api.routes import chat, health, stocks
from backend.rag.ingestion.universe import universe

log = structlog.get_logger()

def _warm_yahoo_session() -> None:
    """Prime curl_cffi session cookies + crumb before first real request."""
    try:
        from backend.rag.yahoo_client import _warm_session, _get_valid_crumb
        ticker = "AAPL"
        _warm_session(ticker)
        crumb = _get_valid_crumb(ticker)
        log.info("yahoo_session_warmed", crumb_ok=bool(crumb))
    except Exception as exc:
        log.warning("yahoo_warm_failed", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", universe_size=len(universe.stocks))

    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _warm_yahoo_session)

    scheduler = None
    if os.getenv("ENV", "development") == "production" or os.getenv("SCHEDULER_ENABLED", "false") == "true":
        from backend.rag.ingestion.scheduler import start_scheduler
        scheduler = start_scheduler()

    yield

    if scheduler:
        from backend.rag.ingestion.scheduler import stop_scheduler
        stop_scheduler()

    log.info("shutdown")


app = FastAPI(title="Finora API", version="1.0.0", lifespan=lifespan)


# ========================= Verify Backend Log (REMOVE LATER) =========================
@app.get("/")
def root():
    return {"message": "Finora API is running"}

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
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)

