# Finora — Test Suite

Three suites: backend unit (no API), backend stress (live backend), frontend unit.

---

## Backend Unit Tests

Zero API calls — tests deterministic logic only.

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt

# All unit tests
pytest ../tests/backend/unit/ -v

# Single file
pytest ../tests/backend/unit/test_fusion_signals.py -v
pytest ../tests/backend/unit/test_intent_classifier.py -v
pytest ../tests/backend/unit/test_guardrails.py -v
```

### What they cover

| File | Coverage |
|---|---|
| `test_fusion_signals.py` | `_compute_narrative_hint`, `_compute_confidence_level`, `_compute_conflict`, `uncertainty_flag`, edge cases |
| `test_intent_classifier.py` | `_is_summary_query` bypass, `_ALL_INTENTS` constant |
| `test_guardrails.py` | `_ALWAYS_BLOCKED` / `_INSIGHT_ONLY_BLOCKED` sets, mode routing |

---

## Backend Stress Tests (Live)

Runs 33 queries × up to 2 modes = up to 66 test cases against a live backend.
Requires backend running at `FINORA_BACKEND_URL` (default: `http://localhost:8000`).

```bash
# Start backend first
cd backend && uvicorn main:app --port 8000

# In another terminal
cd backend
source .venv/bin/activate

# Full stress suite
FINORA_BACKEND_URL=http://localhost:8000 pytest ../tests/backend/stress/test_suite.py -v

# Single category
pytest ../tests/backend/stress/test_suite.py -v -k "insight_guardrail"
pytest ../tests/backend/stress/test_suite.py -v -k "trader_directional"
pytest ../tests/backend/stress/test_suite.py -v -k "adversarial"

# Different ticker
STRESS_TEST_TICKER=MSFT pytest ../tests/backend/stress/test_suite.py -v

# Save report
FINORA_BACKEND_URL=http://localhost:8000 \
  pytest ../tests/backend/stress/test_suite.py -v --tb=short \
  2>&1 | tee ../tests/stress_report.txt

# Quick sanity (health + basic chat + summarize checks, no full suite)
pytest ../tests/backend/stress/test_suite.py -v -k "not test_stress"
```

### Stress test categories (12)

| ID prefix | Category | Mode |
|---|---|---|
| DS-01..04 | Dominant signal override | both |
| LS-01..03 | Low signal / flat day | both |
| CF-01..03 | Conflict + uncertainty | both |
| CG-01..03 | Confidence gradient | both |
| TM-01..03 | Trader directional bias | trader |
| IG-01..04 | Insight guardrail enforcement | insight |
| TB-01..03 | Trader buy/sell — controlled | trader |
| AR-01..02 | Anti-redundancy | both |
| CS-01..02 | Compression stress | both |
| NI-01..02 | Narrative integrity | both |
| MT-01..03 | Multi-turn consistency | both |
| AO-01..04 | Adversarial / override | mixed |

### Behavioral validators (always run on every query)

| Validator | What it catches |
|---|---|
| `assert_no_hallucination` | "sector average", "analysts unanimously", "guaranteed", model breaking character |
| `assert_insight_guardrail` | Missing exact disclaimer phrase, any absolute directive in INSIGHT mode |
| `assert_trader_bias_present` | Missing bullish/bearish/neutral in TRADER directional queries |
| `assert_no_absolute_directive` | "you should buy/sell", "buy now", "go long now", etc. |
| `assert_not_generic` | "mixed signals", "it depends", "various factors" in opening 300 chars |

### Structural snapshots (`TestSummarySnapshots`)

Validate that format/structure doesn't regress across runs:
- `>= 3` section headers present in insight summary
- `Signals That Matter` section always in trader summary
- Zero emojis in any response
- No section body > 5 sentences (compression rule enforced)
- No hallucination markers in summary
- Explicit directional bias in trader directional queries

### Behavioral validation (`TestBehavioralValidation`)

- Insight buy/sell queries trigger exact guardrail phrase
- Trader buy queries contain no absolute directive
- Adversarial jailbreak attempt stays guarded
- No hallucination in directional queries
- Opening never generic/hedge phrase
- Trader entry queries always include risk context

---

## Frontend Unit Tests

TypeScript tests — no browser, no Next.js runtime.

```bash
cd frontend
npm install

# All frontend tests
npm test

# Watch mode
npm run test:watch
```

### What they cover

| File | Coverage |
|---|---|
| `streaming.test.ts` | `ChatMessage` interface shape, `UserMode` type, SSE line parsing, request body construction |

---

## Quick pass — all unit tests at once

```bash
# Backend unit
cd backend && source .venv/bin/activate
pytest ../tests/backend/unit/ -v

# Frontend unit
cd ../frontend
npx jest tests/frontend/

# Both return exit 0 before deploying
```

---

## Adding new tests

- **Backend unit:** add file to `tests/backend/unit/`, import from `backend/` via `sys.path.insert`
- **Stress query:** add `StressQuery(...)` entry to `tests/backend/stress/queries.py` — automatically picked up by parameterized runner
- **Frontend:** add `*.test.ts` to `tests/frontend/__tests__/`
