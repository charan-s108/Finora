<div align="center">

<pre>
███████╗██╗███╗   ██╗ ██████╗ ██████╗  █████╗
██╔════╝██║████╗  ██║██╔═══██╗██╔══██╗██╔══██╗
█████╗  ██║██╔██╗ ██║██║   ██║██████╔╝███████║
██╔══╝  ██║██║╚██╗██║██║   ██║██╔══██╗██╔══██║
██║     ██║██║ ╚████║╚██████╔╝██║  ██║██║  ██║
╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
</pre>

**Production-grade AI equities intelligence for NRI & global investors.**

*RAG · LangGraph · LangSmith · Groq · Recharts · MCP · Real-time · RAGAS*

---

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=next.js)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-1C3A5E?style=flat-square)](https://langchain-ai.github.io/langgraph)
[![LangSmith](https://img.shields.io/badge/LangSmith-Traced-F5A623?style=flat-square)](https://smith.langchain.com)
[![Groq](https://img.shields.io/badge/Groq-llama--3.3--70b-F55036?style=flat-square)](https://groq.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector--Store-E8562A?style=flat-square)](https://qdrant.tech)
[![RAGAS](https://img.shields.io/badge/RAGAS-Evaluation-4CAF50?style=flat-square)](https://github.com/explodinggradients/ragas)

</div>

---

## What Is Finora?

Finora is a **production-grade AI equities intelligence platform** built for NRI and global investors. Not a demo. Not a notebook. A real system built to production RAG standards — typed, traced, tested, and deployed.

**Two products in one:**

- **Dashboard** — Premium dark-mode stock intelligence UI covering 555+ stocks (S&P 500 + NIFTY 50). Real-time price, fundamentals, analyst consensus, 20-year historical patterns, live news RAG, and candlestick charts with 9 timeframes.
- **Finora AI** — Bottom-right floating chatbot with two user modes. Routes every query through a five-layer retrieval system: live market data, 20yr OHLCV patterns, news RAG, SEC filings, and structured fundamentals — fused, reranked, then sent to Groq. Every run traced in LangSmith.

---

## Finora AI — User Modes

The chatbot exposes two distinct behavioral modes, selectable in the chat panel:

### INSIGHT Mode (default)
For everyday investors. Provides analysis, context, and market intelligence. Buy/sell queries are redirected with a clear guardrail — the system surfaces what analysts say and key metrics instead of giving personal financial advice. Every guardrail response ends with the exact phrase: *"Consider consulting a financial advisor before making investment decisions."*

### TRADER Mode
For active traders. Provides explicit directional signals — bullish / bearish / neutral — grounded in volume, momentum, and technical context. Buy/sell queries receive signal-grounded analysis with risk context. No absolute directives ("you should buy") are ever given, but the system answers: *"momentum is bullish, volume confirms, key risk is..."*

Mode is sent with every request as `user_mode: "insight" | "trader"` and drives both the system prompt behavior and the guardrail routing — different blocked intent sets per mode.

---

## Architecture

## Architecture

<p align="center">
  <img src="finora-frontend/public/architecture.png" alt="Finora Architecture Diagram" width="100%" />
</p>

---

## RAG Pipeline — Five Layers Deep

### 1. Intent Classification
Every query → `llama-3.1-8b-instant` (~200ms) → one or more intents → parallel LangGraph branches:
`REAL_TIME | NEWS | HISTORICAL | FUNDAMENTAL`

**Summary bypass:** Queries matching "summarize", "overview", "what's happening", "explain this stock", etc. skip the LLM classifier entirely and return all 4 intents deterministically — no wasted LLM call, no mis-classification.

Multi-intent: *"Compare AAPL and MSFT earnings history"* → `[HISTORICAL, FUNDAMENTAL]` → 2 parallel branches run concurrently.

### 2. Pre-Computed Signal Layer (Fusion Node)
Before sending anything to the LLM, the fusion node deterministically computes:

- **`narrative_hint`** — dominant signal label: `sharp_downward_move | sharp_upward_move | high_volume_move | near_52w_high | near_52w_low | analyst_strongly_bullish | analyst_bearish | mild_upward_move | mild_downward_move | consolidating` — priority-ranked, not guessed
- **`confidence_level`** — `high` (3+ strong signals, 3+ data sources) / `medium` / `low`
- **`conflict`** — detects 4 conflict patterns: price down + analysts bullish, price up + analysts cautious, near 52W low + analysts bullish, near 52W high + target below price
- **`uncertainty_flag`** — true when confidence is low or unresolved conflict exists

These values drive the LLM prompt behavior — the model is told what signals dominate, not asked to figure it out. This eliminates hedging on high-confidence data and prevents fabrication on low-signal days.

### 3. Hybrid Retrieval — BM25 + Dense Vector + RRF
Dense vectors (MiniLM-L6-v2) catch semantic similarity. BM25 catches exact ticker/date matches. **Reciprocal Rank Fusion** merges both. BM25 catches "AAPL on 2022-01-14"; dense catches "when did Apple last see a similar drawdown."

### 4. Cross-Encoder Reranking
Over-retrieve 2× TOP_K → rerank with **Cohere rerank-english-v3.0** (primary) → falls back to `BAAI/bge-reranker-base` locally on rate-limit or failure. Cross-encoders see the full query-passage pair simultaneously — largest single quality improvement in any RAG system.

### 5. MMR Deduplication
Maximal Marginal Relevance (λ=0.6) ensures final TOP_K chunks are both relevant *and* diverse. Prevents the LLM from receiving 8 near-identical articles about the same catalyst.

---

## Chat Features

- **INSIGHT / TRADER mode toggle** — in chat panel header; drives entire response behavior
- **Streaming SSE** — token-by-token with intent badges shown during retrieval
- **"Summarize this stock" chip** — prominent primary chip; triggers full structured narrative across all 4 RAG branches
- **Context-aware suggestion chips** — dynamic follow-up chips per ticker intent
- **Narrative-first structure** — every response leads with the dominant signal, not a generic opening
- **Guardrail redirects** — INSIGHT mode buy/sell queries get signal context + exact disclaimer phrase, never a refusal
- **Conversation memory** — last 4 turns injected into fusion prompt for contextual follow-ups
- **Dynamic price charts** — embedded Recharts AreaChart matched to the query timeframe
- **Smart citations** — news sources shown only on queries with news/movement intent
- **SEBI/SEC disclaimers** — auto-injected, locale-aware

---

## Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14 App Router · TypeScript · Tailwind CSS · shadcn/ui |
| **Charts** | Recharts — candlestick OHLCV + dynamic chat area charts |
| **Backend** | FastAPI · Python 3.11 · Pydantic v2 · Uvicorn |
| **Agent Graph** | LangGraph 0.2 StateGraph — parallel branches, typed state |
| **RAG** | LangChain v0.3 · Hybrid BM25+Dense · HyDE · Cohere rerank · BAAI fallback |
| **Observability** | LangSmith — every graph run traced |
| **RAG Evaluation** | RAGAS 0.2.5 — faithfulness, answer relevancy, context recall, context precision, noise sensitivity |
| **LLM Primary** | Groq `llama-3.3-70b-versatile` — response generation |
| **LLM Fast** | Groq `llama-3.1-8b-instant` — intent classification, guardrails, HyDE |
| **Embeddings** | HuggingFace `all-MiniLM-L6-v2` — local, free, no API key |
| **Vector Store** | Qdrant Cloud (free 1GB cluster) |
| **MCP** | FastMCP server — 6 tools: quote, historical RAG, news RAG, fundamentals, screener, universe |
| **Real-time Data** | Yahoo Finance via `curl_cffi` Chrome TLS impersonation — no API key needed |
| **News** | Google News RSS — live, locale-aware (NSE/BSE for Indian stocks) |
| **Historical** | 20yr weekly OHLCV via Yahoo Finance → FinancialEventChunker → Qdrant |
| **Scheduling** | APScheduler — news every 15min, historical daily |
| **Guardrails** | `llama-3.1-8b` input classifier + mode-aware blocked intents + output hallucination check + PII scrub |
| **Deploy** | Vercel (frontend) · Railway (backend) |

---

## Project Structure

```
finora/
├── .gitignore
├── docker-compose.yml
├── README.md
│
├── finora-backend/
│   ├── main.py               ← FastAPI app + lifespan (Yahoo warm-up, scheduler)
│   ├── requirements.txt
│   ├── requirements-dev.txt  ← pytest, ruff, black, mypy (not in Docker)
│   ├── Dockerfile
│   │
│   ├── api/routes/
│   │   ├── chat.py           ← POST /api/chat — SSE, user_mode field, chart_data, citation gating
│   │   ├── stocks.py         ← GET /api/stocks/search, /{ticker}, /{ticker}/ohlcv
│   │   └── health.py         ← GET /api/health (real Groq ping)
│   │
│   ├── graph/
│   │   ├── finora_graph.py   ← LangGraph StateGraph topology
│   │   ├── state.py          ← FiNoraState TypedDict (includes user_mode: UserMode)
│   │   └── nodes/
│   │       ├── intent_classifier.py  ← Summary bypass + llama-3.1-8b classification
│   │       ├── fusion_node.py        ← Pre-computed signals + data context builder
│   │       └── response_node.py      ← Mode-split system prompts (INSIGHT / TRADER)
│   │
│   ├── rag/
│   │   ├── retrieval/        ← hybrid, hyde, reranker, dedup, router
│   │   ├── chunking/         ← sliding_window, semantic, financial_event
│   │   ├── ingestion/        ← historical, news, filings, universe, scheduler
│   │   └── evaluation/       ← ragas_eval, synthetic QA generator
│   │
│   ├── guardrails/
│   │   ├── classifier.py     ← _ALWAYS_BLOCKED + _INSIGHT_ONLY_BLOCKED sets
│   │   ├── output_filter.py  ← Hallucination check + PII scrub + grounding
│   │   └── disclaimers.py    ← SEBI/SEC templates + injector
│   │
│   ├── mcp/                  ← FastMCP server + 6 tool definitions
│   ├── observability/        ← LangSmith trace wrapper
│   └── scripts/
│       ├── build_universe.py
│       ├── ingest_historical.py
│       ├── ingest_news.py
│       └── eval_rag.py
│
├── finora-frontend/
│   ├── jest.config.js        ← next/jest wrapper, tests/ root override
│   ├── app/
│   │   ├── icon.svg          ← Favicon (Next.js App Router auto-detection)
│   │   └── dashboard/[ticker]/
│   │       ├── page.tsx      ← SSR stock detail, notFound() on bad ticker
│   │       ├── loading.tsx   ← Skeleton layout during SSR fetch
│   │       └── error.tsx     ← Branded error page for invalid tickers
│   │
│   ├── components/
│   │   ├── dashboard/        ← StockSearch, StockHeader, PriceChart, FundamentalsGrid,
│   │   │                        NewsRagPanel, HistoricalRagPanel, AnalystConsensus,
│   │   │                        StockAbout, SectorHeatmap
│   │   └── chat/
│   │       ├── ChatWidget.tsx      ← FAB + panel, INSIGHT/TRADER mode state
│   │       ├── ChatMessage.tsx     ← Markdown, embedded price charts, citations
│   │       ├── ChatInput.tsx       ← Mode toggle UI + send
│   │       └── SuggestionChips.tsx ← "Summarize this stock" primary chip + follow-ups
│   │
│   └── lib/
│       ├── api.ts            ← Typed fetch client, Zod schemas
│       └── streaming.ts      ← SSE parser, ChatMessage type, UserMode type, streamChat()
│
└── tests/
    ├── README.md             ← How to run each suite
    ├── backend/
    │   ├── conftest.py       ← make_state() fixture builder
    │   ├── unit/             ← No API calls — deterministic logic only
    │   │   ├── test_fusion_signals.py     ← 40+ signal computation tests
    │   │   ├── test_intent_classifier.py  ← Summary bypass + _ALL_INTENTS
    │   │   └── test_guardrails.py         ← Blocked intent sets, mode routing
    │   ├── integration/
    │   │   └── test_pipeline.py           ← Full pipeline, Groq mocked
    │   └── stress/                        ← Live backend tests (requires running backend)
    │       ├── queries.py    ← 33 StressQuery objects across 12 behavior categories
    │       └── test_suite.py ← Parameterized runner with behavioral validators,
    │                            structural snapshots, hallucination checks,
    │                            guardrail enforcement, failure logging
    └── frontend/
        └── __tests__/
            └── streaming.test.ts  ← 16 tests — SSE parsing, ChatMessage shape, UserMode
```

---

## Testing (Optional)

Finora ships a comprehensive test suite covering unit tests, integration tests, and stress testing. For details on running tests, see [`tests/README.md`](tests/README.md).

**Test coverage:**
- **Backend unit** — Deterministic logic (fusion signals, intent classifier, guardrails) — runs offline, < 1s
- **Backend integration** — Full pipeline with Groq mocked
- **Frontend unit** — 16 tests (ChatMessage, SSE parsing, UserMode type)
- **Stress tests** — 33 queries × 2 modes → 12 behavioral categories against live backend

---

## RAG Evaluation — RAGAS

Finora RAG pipeline is evaluated offline using [RAGAS](https://docs.ragas.io/). Results visible at `/eval` page in production UI.

**Current status:** All 4 metrics **PASS** ✓

| Metric | Score | Target | Status |
|---|---|---|---|
| Faithfulness | 0.94 | 0.85 | ✓ |
| Answer Relevancy | 0.86 | 0.80 | ✓ |
| Context Recall | 0.98 | 0.75 | ✓ |
| Context Precision | 0.99 | 0.70 | ✓ |

Evaluated across: `AAPL, RELIANCE, INFY, META` — 12 synthetic QA pairs generated from Qdrant chunks.

For how to run custom RAGAS evals, see [`tests/README.md`](tests/README.md).

---

## Quickstart

### Prerequisites
Python 3.11+, Node.js 20+

### 1. Clone & Configure

```bash
git clone https://github.com/charan-s108/Finora.git
cd Finora
cp finora-backend/.env.example finora-backend/.env
# Fill in: GROQ_API_KEY, QDRANT_URL, QDRANT_API_KEY, LANGCHAIN_API_KEY
```

### 2. Backend

```bash
cd finora-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Build stock universe (required first — ~555 stocks → stocks.json)
python scripts/build_universe.py

# Seed historical RAG data (~30 min for full list)
python scripts/ingest_historical.py --tickers AAPL MSFT NVDA RELIANCE TCS INFY --years 20

# Seed news corpus
python scripts/ingest_news.py --tickers AAPL MSFT NVDA

# Start backend
uvicorn main:app --reload --port 7860
```

### 3. finora-frontend

```bash
cd finora-frontend
npm install
echo "NEXT_PUBLIC_BACKEND_URL=http://localhost:7860" > .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 4. Docker (Full Stack)

```bash
docker-compose up --build
```

---

## Production Deploy

### finora-backend → Railway

```bash
npm install -g @railway/cli
railway login
cd finora-backend && railway init
railway up

railway variables set GROQ_API_KEY=gsk_...
railway variables set GROQ_MODEL_PRIMARY=llama-3.3-70b-versatile
railway variables set GROQ_MODEL_FAST=llama-3.1-8b-instant
railway variables set LANGCHAIN_API_KEY=ls__...
railway variables set LANGCHAIN_PROJECT=finora-prod
railway variables set LANGCHAIN_TRACING_V2=true
railway variables set QDRANT_URL=https://your-cluster.qdrant.io:6333
railway variables set QDRANT_API_KEY=...
railway variables set GUARDRAILS_ENABLED=true
railway variables set DISCLAIMER_LOCALE=IN
railway variables set CORS_ORIGINS=https://finora.vercel.app
railway variables set ENV=production

railway domain   # → finora-backend.up.railway.app
```

### Frontend → Vercel

```bash
npm install -g vercel
cd finora-frontend && vercel
vercel env add NEXT_PUBLIC_BACKEND_URL   # https://finora-backend.up.railway.app
vercel --prod
```

### Verify

```bash
curl https://finora-backend.up.railway.app/api/health
# → {"status":"ok","groq":"connected","qdrant":"connected","universe_size":555}
```

---

## Observability

### LangSmith — Every Run Traced

All LangGraph runs are automatically traced when `LANGCHAIN_TRACING_V2=true`.

- View all traces: `https://smith.langchain.com/projects/finora-prod`
- Each chat response includes a **"LangSmith trace ↗"** link in the UI
- Traces show: intent classification → retrieval latency → reranking → fusion → generation

### RAGAS Evaluation

```bash
cd finora-backend
python scripts/eval_rag.py --tickers AAPL MSFT RELIANCE.NS --n 5
```

| Metric | Target |
|---|---|
| Faithfulness | > 0.85 |
| Answer Relevance | > 0.80 |
| Context Recall | > 0.75 |
| Context Precision | > 0.70 |
| Noise Sensitivity | < 0.15 |

---

## API Reference

### `POST /api/chat` — SSE Stream

```json
{
  "query": "Why did AAPL drop today?",
  "ticker": "AAPL",
  "conversation_history": [],
  "session_id": "uuid",
  "user_mode": "insight"
}
```

Stream events: `guardrail → intent → retrieving → token... → chart_data → citation → disclaimer → done`

### `GET /api/stocks/search?q=apple&limit=10`
Fuzzy search across 555 stocks. Returns ticker, name, exchange, sector, country.

### `GET /api/stocks/{ticker}`
Full snapshot: price, fundamentals, analyst consensus, 7-day OHLCV, live news, historical RAG signals.

### `GET /api/stocks/{ticker}/ohlcv?range=1M`
OHLCV bars for any timeframe: `1D | 1W | 1M | 3M | 6M | 1Y | 3Y | 5Y | ALL`

### `GET /api/health`
Real connectivity checks — Groq (1-token ping), Qdrant (list collections).

---

## Guardrails

**Mode-aware blocking:**

| Intent | INSIGHT | TRADER |
|---|---|---|
| `direct_buy_sell_recommendation` | Blocked → redirect with disclaimer | Allowed → signals + risk context |
| `personal_financial_planning` | Blocked → redirect | Allowed |
| `insider_trading_context` | Blocked | Blocked |
| `market_manipulation` | Blocked | Blocked |
| `tax_evasion_advice` | Blocked | Blocked |
| `specific_options_strategy` | Blocked | Blocked |

**Output guardrails (post-generation):**
- Hallucination check — numbers in response verified against `fused_context`
- PII scrub — Aadhaar, PAN card, account numbers redacted
- Confidence signal — low retrieval score surfaces warning in UI
- No emojis enforced via system prompt rule

---

## MCP Server

```bash
cd finora-backend && python -m mcp.server
```

| Tool | Description |
|---|---|
| `get_realtime_quote(ticker)` | Live price, volume, intraday OHLC |
| `search_historical_rag(ticker, query, years)` | 20yr OHLCV event chunks, reranked |
| `search_news_rag(ticker, query, days)` | News + filings, reranked, deduplicated |
| `get_fundamentals(ticker)` | PE, EPS, margins, analyst consensus |
| `screen_stocks(sector, min_pe, max_pe, country)` | Filter 555-stock universe |
| `get_stock_universe(query, limit)` | Fuzzy search by name or ticker |

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

Built by [Charan](https://github.com/charan-s108) · Powered by Groq · Traced by LangSmith

*"AI isn't a feature — it's the product."*

</div>
