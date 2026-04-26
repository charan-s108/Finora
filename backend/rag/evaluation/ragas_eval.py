"""
RAGAS evaluation runner for Finora RAG pipeline.

Targets:
    Faithfulness       > 0.85
    Answer Relevance   > 0.80
    Context Recall     > 0.75
    Context Precision  > 0.70
    Noise Sensitivity  < 0.15

Usage:
    from rag.evaluation.ragas_eval import run_ragas_eval
    results = run_ragas_eval(qa_pairs, tickers=["AAPL", "MSFT"])
"""
from __future__ import annotations

import os
from typing import Any

import structlog

log = structlog.get_logger()

TARGETS = {
    "faithfulness": 0.85,
    "answer_relevancy": 0.80,
    "context_recall": 0.75,
    "context_precision": 0.70,
    "noise_sensitivity": 0.15,  # must be BELOW this
}


def run_ragas_eval(
    qa_pairs: list[dict],
    tickers: list[str] | None = None,
) -> dict[str, Any]:
    """
    Run RAGAS evaluation over a list of QA pairs.

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

    dataset = Dataset.from_list(qa_pairs)

    metrics = [faithfulness, answer_relevancy, context_recall, context_precision]

    try:
        result = evaluate(dataset, metrics=metrics)
        scores: dict[str, float] = dict(result)
    except Exception as exc:
        log.error("ragas_eval_failed", error=str(exc))
        return {"error": str(exc)}

    report: dict[str, Any] = {"scores": scores, "results": {}}
    for metric, target in TARGETS.items():
        score = scores.get(metric)
        if score is None:
            continue
        if metric == "noise_sensitivity":
            passed = score < target
        else:
            passed = score >= target
        report["results"][metric] = {
            "score": round(score, 4),
            "target": target,
            "passed": passed,
        }

    all_pass = all(r["passed"] for r in report["results"].values())
    report["overall_pass"] = all_pass
    log.info("ragas_eval_complete", pass_all=all_pass, scores=scores)
    return report
