"""
RAGAS evaluation runner for Finora RAG pipeline.

Uses Groq llama-3.1-8b-instant (GROQ_MODEL_FAST) as the evaluation LLM
and all-MiniLM-L6-v2 (local HF) for embeddings — zero OpenAI dependency.

Targets:
    Faithfulness       > 0.85
    Answer Relevance   > 0.80
    Context Recall     > 0.75
    Context Precision  > 0.70

Usage:
    from backend.rag.evaluation.ragas_eval import run_ragas_eval
    results = run_ragas_eval(qa_pairs, tickers=["AAPL", "MSFT"])
"""
from __future__ import annotations

import os
import warnings
from typing import Any

import structlog

log = structlog.get_logger()

TARGETS = {
    "faithfulness":      0.85,
    "answer_relevancy":  0.80,
    "context_recall":    0.75,
    "context_precision": 0.70,
}


def _build_llm():
    """Groq llama-3.1-8b-instant wrapped for RAGAS.

    Groq rejects n > 1. RAGAS passes n=3 via LangchainLLMWrapper.generate(n=3).
    Subclass the wrapper itself to hard-cap n=1 at the exact call site.
    """
    from langchain_groq import ChatGroq
    from ragas.llms import LangchainLLMWrapper

    groq = ChatGroq(
        model=os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant"),
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.0,
        max_tokens=512,
        n=1,
    )

    return LangchainLLMWrapper(groq, bypass_n=True)


def _build_embeddings():
    """Local all-MiniLM-L6-v2 wrapped for RAGAS — no API key needed."""
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper

    return LangchainEmbeddingsWrapper(HuggingFaceEmbeddings(
        model_name=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        cache_folder=os.getenv("HF_CACHE_DIR", "data/hf_cache"),
    ))


def run_ragas_eval(
    qa_pairs: list[dict],
    tickers: list[str] | None = None,
) -> dict[str, Any]:
    """
    Run RAGAS evaluation over QA pairs.

    qa_pairs schema:
        [{"question": str, "answer": str, "contexts": list[str], "ground_truth": str}]

    Returns metrics dict with scores + pass/fail per metric.
    """
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
    except ImportError as exc:
        log.error("ragas_import_failed", error=str(exc))
        return {"error": "ragas / datasets not installed"}

    if not qa_pairs:
        return {"error": "no QA pairs provided"}

    try:
        llm = _build_llm()
        embeddings = _build_embeddings()
    except Exception as exc:
        log.error("ragas_llm_build_failed", error=str(exc))
        return {"error": f"LLM/embeddings init failed: {exc}"}

    dataset = Dataset.from_list(qa_pairs)

    # Cap answer_relevancy to n=1 — Groq free tier can't handle n=3 sequential calls
    answer_relevancy.n = 1  # type: ignore[attr-defined]

    metrics = [faithfulness, answer_relevancy, context_recall, context_precision]

    log.info("ragas_eval_start", pairs=len(qa_pairs), tickers=tickers)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = evaluate(
                dataset,
                metrics=metrics,
                llm=llm,
                embeddings=embeddings,
                raise_exceptions=False,
                show_progress=True,
            )
        # EvaluationResult is DataFrame-like — extract per-row scores then average
        result_df = result.to_pandas()
        metric_cols = [c for c in result_df.columns if c in TARGETS]
        scores: dict[str, float] = result_df[metric_cols].mean().dropna().to_dict()
    except Exception as exc:
        log.error("ragas_eval_failed", error=str(exc))
        return {"error": str(exc)}

    report: dict[str, Any] = {"scores": scores, "results": {}}
    for metric, target in TARGETS.items():
        score = scores.get(metric)
        if score is None:
            continue
        report["results"][metric] = {
            "score": round(score, 4),
            "target": target,
            "passed": score >= target,
            "delta": round(score - target, 4),
        }

    all_pass = all(r["passed"] for r in report["results"].values())
    report["overall_pass"] = all_pass
    report["tickers"] = tickers or []
    report["n_pairs"] = len(qa_pairs)

    log.info("ragas_eval_complete", pass_all=all_pass, scores=scores)
    return report
