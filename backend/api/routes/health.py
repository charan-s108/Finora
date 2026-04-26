import json
import os
from pathlib import Path

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from rag.ingestion.universe import universe

log = structlog.get_logger()
router = APIRouter(tags=["health"])

_LANGSMITH_PROJECT = os.getenv("LANGCHAIN_PROJECT", "finora-prod")
_EVAL_PATH = Path(__file__).parent.parent.parent / "data" / "eval_results" / "latest.json"


class HealthResponse(BaseModel):
    status: str
    qdrant: str
    groq: str
    langsmith: str
    langsmith_url: str
    universe_size: int


class EvalMetric(BaseModel):
    score: float
    target: float
    passed: bool


class EvalResponse(BaseModel):
    overall_pass: bool
    scores: dict[str, float]
    results: dict[str, EvalMetric]
    run_at: str | None = None


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    qdrant_status = "unconfigured"
    groq_status = "unconfigured"
    langsmith_status = "unconfigured"
    langsmith_url = f"https://smith.langchain.com/projects/{_LANGSMITH_PROJECT}"

    if os.getenv("QDRANT_URL") and os.getenv("QDRANT_API_KEY"):
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(
                url=os.getenv("QDRANT_URL"),
                api_key=os.getenv("QDRANT_API_KEY"),
                timeout=3,
            )
            client.get_collections()
            qdrant_status = "connected"
        except Exception as exc:
            log.warning("qdrant_health_failed", error=str(exc))
            qdrant_status = "error"

    if os.getenv("GROQ_API_KEY"):
        try:
            from groq import Groq
            groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            groq_status = "connected"
        except Exception as exc:
            log.warning("groq_health_failed", error=str(exc))
            groq_status = "error"

    if os.getenv("LANGCHAIN_API_KEY"):
        langsmith_status = "configured"

    return HealthResponse(
        status="ok",
        qdrant=qdrant_status,
        groq=groq_status,
        langsmith=langsmith_status,
        langsmith_url=langsmith_url,
        universe_size=len(universe.stocks),
    )


@router.get("/eval/latest", response_model=EvalResponse)
async def eval_latest() -> EvalResponse:
    """Return most recent RAGAS evaluation results from disk."""
    if not _EVAL_PATH.exists():
        return EvalResponse(
            overall_pass=False,
            scores={},
            results={},
            run_at=None,
        )
    try:
        data = json.loads(_EVAL_PATH.read_text())
        return EvalResponse(
            overall_pass=data.get("overall_pass", False),
            scores=data.get("scores", {}),
            results={
                k: EvalMetric(**v)
                for k, v in data.get("results", {}).items()
            },
            run_at=data.get("run_at"),
        )
    except Exception as exc:
        log.warning("eval_read_failed", error=str(exc))
        return EvalResponse(overall_pass=False, scores={}, results={}, run_at=None)
