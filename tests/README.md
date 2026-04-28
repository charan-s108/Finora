# Finora Test Suite

Complete testing guide for Finora backend and frontend. Tests are **optional** for running the product — they're tools for validating changes, not blockers for deployment.

---

## Quick Start

```bash
# Backend unit tests (offline, <1s)
cd backend && pytest ../tests/backend/unit/ -v

# Frontend tests
cd frontend && npm test

# Stress tests (requires running backend)
cd backend && FINORA_BACKEND_URL=http://localhost:7860 pytest ../tests/backend/stress/test_suite.py -v
```

---

## Backend Unit Tests

**Run offline. No API calls. Fully deterministic. ~1 second.**

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt

pytest ../tests/backend/unit/ -v
```

### Coverage

| File | Tests | What it validates |
|---|---|---|
| `test_fusion_signals.py` | 40+ | `_compute_narrative_hint` (all 10 label outputs: sharp_downward_move, sharp_upward_move, near_52w_high, analyst_strongly_bullish, etc.), `_compute_confidence_level` (high/medium/low thresholds), `_compute_conflict` (all 4 patterns: price down + analysts bullish, price up + analysts cautious, near 52W low + analysts bullish, near 52W high + target below price), `uncertainty_flag` edge cases |
| `test_intent_classifier.py` | 12 | `_is_summary_query` trigger word detection ("summarize", "overview", "explain", etc.), non-trigger focused queries (should not trigger summary bypass), `_ALL_INTENTS` routing constant |
| `test_guardrails.py` | 8 | `_ALWAYS_BLOCKED` / `_INSIGHT_ONLY_BLOCKED` intent sets, no overlap invariant, mode-based routing (insight mode blocks buy/sell, trader allows) |

**Run one test file:**
```bash
pytest ../tests/backend/unit/test_fusion_signals.py -v
pytest ../tests/backend/unit/test_intent_classifier.py -v
pytest ../tests/backend/unit/test_guardrails.py -v
```

---

## Backend Integration Tests

**Groq mocked. Pipeline end-to-end. Tests state schema, system prompts, guardrail mode-awareness.**

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt

pytest ../tests/backend/integration/ -v
```

### Coverage

| Component | Validated |
|---|---|
| **Guardrail Mode-Awareness** | TRADER mode allows buy/sell queries through. INSIGHT mode blocks and redirects with disclaimer. |
| **Intent Classifier Summary Bypass** | "Summarize this stock" / "What's happening" → skip LLM, return all 4 intents |
| **Fusion Signal Computation** | Pre-computed signals reach LLM prompt correctly. No lossy transformations. |
| **Response Node System Prompts** | INSIGHT prompt enforces disclaimer phrase. TRADER prompt includes directional signals. No emojis in either mode. |
| **State Schema Integrity** | `user_mode` field present. Removed fields (`summaryCard`) absent. |

**Run:**
```bash
pytest ../tests/backend/integration/test_pipeline.py -v
```

---

## Frontend Unit Tests

**Jest + SWC. Tests ChatMessage shape, SSE parsing, UserMode type enforcement, streaming behavior.**

```bash
cd frontend
npm install
npm test
```

### Coverage (16 tests)

| Test Group | Validates |
|---|---|
| `ChatMessage interface` | Required fields present. Removed fields absent (`summaryCard`, `c1Content`). `isAutoSummary` flag. `chartData` shape with `PriceBar` type. |
| `UserMode type` | `"insight"` and `"trader"` are valid. Type enforced (TypeScript). |
| `SSE event parsing` | `token` events accumulated correctly. `intent` badge mapping. `done` event extracts confidence score. `chart_data` events parsed. Malformed JSON → null graceful. Non-data lines ignored. |
| `streamChat request body` | `user_mode` propagated in request. `conversation_history` is array. Ticker passed correctly. |

**Run:**
```bash
cd frontend && npm test -- streaming.test.ts
```

**Watch mode:**
```bash
npm test -- --watch
```

---

## Stress Test Suite

**Live backend. 33 queries × 2 modes. 12 behavioral categories. Full guardrail + hallucination validation.**

**Requires:** Running backend (`uvicorn main:app --port 7860`)

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
python main.py  # or: uvicorn main:app --port 7860

# In another terminal:
cd backend
FINORA_BACKEND_URL=http://localhost:7860 \
STRESS_TEST_DELAY=2.5 \
pytest ../tests/backend/stress/test_suite.py -v
```

### Test Categories (33 queries)

| Category | Queries | Validates |
|---|---|---|
| **Dominant Signal** | DS-01..04 | Large move dominates narrative. No signal dilution. Emphasis matches magnitude. |
| **Low Signal** | LS-01..03 | No fabricated story on flat days. Honest "consolidating" / "no clear catalyst". |
| **Conflict** | CF-01..03 | Price down + analysts bullish → explicitly named divergence. Not hedged. |
| **Confidence Gradient** | CG-01..03 | Language certainty matches signal strength. High confidence = fewer hedges. |
| **Trader Directional** | TM-01..03 | Explicit bullish/bearish/neutral bias. Signals + risk context. Volume confirmation. |
| **Insight Guardrail** | IG-01..04 | Exact disclaimer phrase: *"Consider consulting a financial advisor before making investment decisions."* |
| **Trader Buy/Sell** | TB-01..03 | Signals + risk given. No absolute directives ("buy now", "you should buy"). |
| **Anti-Redundancy** | AR-01..02 | Each section adds new info. No repetition across narrative. |
| **Compression** | CS-01..02 | Sections stay 1-2 sentences despite "tell me everything". Focus maintained. |
| **Narrative Integrity** | NI-01..02 | Opening anchored to actual signal, not generic hedge like "mixed signals". |
| **Multi-turn** | MT-01..03 | Consistency across follow-up challenges. No contradictions. |
| **Adversarial** | AO-01..04 | Jailbreak / override attempts blocked. Guardrail + mode enforcement. |

### Behavioral Validators

Every test runs these checks:

```python
assert_no_hallucination(response)
    # Rejects: "sector average", "analysts unanimously", "guaranteed", 
    #          model breaking character, unverified numbers

assert_insight_guardrail(response)
    # INSIGHT mode: exact phrase required
    # "Consider consulting a financial advisor before making investment decisions."

assert_trader_bias_present(response)
    # TRADER mode: bullish/bearish/neutral required for directional queries

assert_no_absolute_directive(response)
    # Forbidden: "you should buy/sell", "buy now", "go long now"
    # In ALL modes

assert_not_generic(response)
    # Opening 300 chars must not be: "mixed signals", "it depends", 
    #                                  "depends on factors"
```

### Structural Snapshots

```python
# Insight summary must have ≥3 section headers
# Trader summary must always have "Signals That Matter"
# Zero emojis in any response
# No section body > 5 sentences
# Trader directional queries must have explicit bias signal
```

### Run Specific Categories

```bash
# All insight guardrail tests
pytest ../tests/backend/stress/test_suite.py -v -k "insight_guardrail"

# All trader tests
pytest ../tests/backend/stress/test_suite.py -v -k "trader"

# Specific test
pytest ../tests/backend/stress/test_suite.py::test_dominant_signal -v

# Write full report
pytest ../tests/backend/stress/test_suite.py -v --tb=short 2>&1 | tee stress_report.txt

# Verbose failure logs
pytest ../tests/backend/stress/test_suite.py -v -s --tb=long
```

**Failure output includes:**
- Query + mode
- Live SSE metadata (intents, guardrail status, confidence score)
- Full response text
- Each specific failure reason (bulleted)
- LangSmith trace URL (clickable)

---

## RAG Evaluation — RAGAS

Evaluate RAG pipeline quality offline using RAGAS metrics.

### Setup

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt  # includes ragas==0.2.5, datasets==3.1.0
```

### Run Evaluation

```bash
# Evaluate news collection (4 tickers, 5 QA pairs each = 20 total)
python scripts/eval_rag.py \
  --tickers AAPL MSFT NVDA RELIANCE.NS \
  --collection news \
  --n 5

# Evaluate historical collection (10 pairs per ticker)
python scripts/eval_rag.py \
  --tickers AAPL MSFT RELIANCE.NS \
  --collection historical \
  --n 10

# Timestamped output
python scripts/eval_rag.py \
  --tickers AAPL MSFT NVDA META RELIANCE INFY \
  --collection historical \
  --n 3 \
  --output backend/data/eval_results/ragas_$(date +%Y%m%d_%H%M%S).json
```

### Metrics & Targets

| Metric | Target | Measures |
|---|---|---|
| **Faithfulness** | > 0.85 | Claims in response grounded in retrieved context. Catches hallucination. |
| **Answer Relevancy** | > 0.80 | Response addresses the actual question. |
| **Context Recall** | > 0.75 | Retrieval surfaced info needed to answer. |
| **Context Precision** | > 0.70 | Retrieved docs are on-topic (not noise). |

### Output Format

```json
{
  "scores": {
    "faithfulness": 0.94,
    "answer_relevancy": 0.86,
    "context_recall": 0.98,
    "context_precision": 0.99
  },
  "results": {
    "faithfulness": {
      "score": 0.94,
      "target": 0.85,
      "passed": true,
      "delta": 0.09
    },
    "answer_relevancy": {
      "score": 0.86,
      "target": 0.80,
      "passed": true,
      "delta": 0.06
    },
    "context_recall": {
      "score": 0.98,
      "target": 0.75,
      "passed": true,
      "delta": 0.23
    },
    "context_precision": {
      "score": 0.99,
      "target": 0.70,
      "passed": true,
      "delta": 0.29
    }
  },
  "overall_pass": true,
  "tickers": ["AAPL", "MSFT", "NVDA", "RELIANCE.NS"],
  "n_pairs": 20,
  "run_at": "2026-04-26T23:45:00.000000Z"
}
```

### How It Works

1. **Generate synthetic QA pairs** from Qdrant chunks via `llama-3.1-8b-instant`
2. **Evaluate** each pair with RAGAS metrics (uses Groq + local HF embeddings)
3. **Compare** each metric score vs target threshold
4. **Report** scores + pass/fail per metric + overall status
5. **Save** to `backend/data/eval_results/latest.json` (used by `/eval` page in UI)

### View Results

Results auto-display at `/eval` page in production UI.

Manually:
```bash
cat backend/data/eval_results/latest.json | jq
```

---

## Test Architecture

### Fixtures & Helpers

**`tests/backend/conftest.py`**
```python
@pytest.fixture
def make_state():
    """Builder for FiNoraState. Use: state = make_state(ticker="AAPL", query="...", user_mode="trader")"""
    def _make(**overrides):
        defaults = {
            "query": "Why did this stock move?",
            "ticker": "AAPL",
            "user_mode": "insight",
            "session_id": "test-session-uuid",
            "conversation_history": [],
            # ... all other FiNoraState fields
        }
        defaults.update(overrides)
        return FiNoraState(**defaults)
    return _make
```

**`tests/backend/stress/queries.py`**
```python
class StressQuery:
    """Single test case: query, mode, expected behavioral validators"""
    query: str
    mode: UserMode
    category: str
    intent_expected: list[str]
    validators: list[ValidatorFunc]
    reason: str  # Why this test matters

# Example: DS-01 (Dominant Signal)
QUERIES = [
    StressQuery(
        query="Apple fell 5% today, any news?",
        mode="insight",
        category="dominant_signal",
        intent_expected=["real_time", "news"],
        validators=[assert_not_generic, assert_dominant_signal_centered],
        reason="Large negative move should lead response. No hedging."
    ),
    # ...33 total
]
```

---

## CI/CD Integration

Tests can be integrated into GitHub Actions:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  backend-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with: { python-version: '3.11' }
      - run: |
          cd backend && python -m venv .venv && source .venv/bin/activate
          pip install -r requirements-dev.txt
          pytest ../tests/backend/unit/ -v

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with: { node-version: '20' }
      - run: cd frontend && npm install && npm test
```

---

## Troubleshooting

### `pytest: command not found`
```bash
source .venv/bin/activate
pip install pytest pytest-asyncio
```

### `ModuleNotFoundError: No module named 'finora'`
```bash
# From backend/ root:
pip install -e .
# Or add to PYTHONPATH:
export PYTHONPATH=/path/to/backend:$PYTHONPATH
```

### Stress tests hanging
- Ensure backend is running: `uvicorn main:app --port 7860`
- Check `FINORA_BACKEND_URL` env var: `echo $FINORA_BACKEND_URL`
- Verify backend is healthy: `curl http://localhost:7860/api/health`

### Frontend tests fail with "Cannot find module '@/'"
```bash
cd frontend
npm install
npm test
```

---

## Test Philosophy

1. **Unit tests** — Fast, offline, deterministic. No API calls. Validate logic.
2. **Integration tests** — Mocked external services. Validate schema + behavior.
3. **Stress tests** — Real backend. Validate user-facing behavior across 33 edge cases.
4. **RAGAS evals** — RAG quality metrics. Not required for deployment, but recommended before major releases.

**Tests are tools, not gates.** Deploy with confidence if you've manually validated the critical path (chat, dashboard, health check). Use tests to catch regressions during development.

---

## Contributing Tests

To add a new stress test:

1. Add `StressQuery` object to `tests/backend/stress/queries.py`
2. Define validator function or reuse existing: `assert_insight_guardrail`, `assert_trader_bias_present`, etc.
3. Run: `pytest ../tests/backend/stress/test_suite.py::test_custom_query -v`

Example:
```python
StressQuery(
    query="Is NVIDIA overbought at new highs?",
    mode="trader",
    category="technical_analysis",
    intent_expected=["real_time", "historical"],
    validators=[
        assert_no_hallucination,
        assert_trader_bias_present,
        assert_technical_context,
    ],
    reason="Trader needs explicit technical bias + risk awareness at extremes"
)
```

---

*Last updated: April 2026*
