#!/usr/bin/env python3
"""
RAGAS evaluation suite for Finora RAG pipeline.

Usage:
    python backend/scripts/eval_rag.py --tickers AAPL MSFT NVDA RELIANCE.NS
    python backend/scripts/eval_rag.py --tickers AAPL --collection historical --n 10
    python backend/scripts/eval_rag.py --tickers AAPL --output backend/data/eval_results/ragas_20260424.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

DEFAULT_LATEST = ROOT / "backend" / "data" / "eval_results" / "latest.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAGAS eval on Finora RAG pipeline")
    parser.add_argument("--tickers", nargs="+", required=True, help="Tickers to evaluate")
    parser.add_argument(
        "--collection",
        default="news",
        choices=["news", "historical", "filings"],
        help="Qdrant collection to sample from (default: news)",
    )
    parser.add_argument("--n", type=int, default=5, help="QA pairs per ticker (default: 5)")
    parser.add_argument("--output", type=str, default=None, help="Path to write JSON results")
    args = parser.parse_args()

    from backend.rag.evaluation.synthetic import generate_synthetic_dataset
    from backend.rag.evaluation.ragas_eval import run_ragas_eval

    print(f"Generating synthetic QA dataset for: {args.tickers}")
    qa_pairs = generate_synthetic_dataset(
        tickers=args.tickers,
        collection_key=args.collection,
        n_per_ticker=args.n,
    )
    print(f"Generated {len(qa_pairs)} QA pairs")

    if not qa_pairs:
        print("No QA pairs generated — check Qdrant data for these tickers.")
        sys.exit(1)

    print("\nRunning RAGAS evaluation...")
    report = run_ragas_eval(qa_pairs, tickers=args.tickers)

    if "error" in report:
        print(f"Eval failed: {report['error']}")
        sys.exit(1)

    print("\n── RAGAS Results ──────────────────────────")
    for metric, result in report.get("results", {}).items():
        status = "✓ PASS" if result["passed"] else "✗ FAIL"
        target_label = f"< {result['target']}" if metric == "noise_sensitivity" else f"> {result['target']}"
        print(f"  {metric:<25} {result['score']:.4f}  (target {target_label})  {status}")
    print(f"\nOverall: {'PASS ✓' if report.get('overall_pass') else 'FAIL ✗'}")

    report["run_at"] = dt.datetime.utcnow().isoformat() + "Z"
    report["tickers"] = args.tickers

    DEFAULT_LATEST.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_LATEST.write_text(json.dumps(report, indent=2))
    print(f"Latest results saved → {DEFAULT_LATEST}")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"qa_pairs": qa_pairs, "report": report}, indent=2))
        print(f"Results saved → {out_path}")


if __name__ == "__main__":
    main()