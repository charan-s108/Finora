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
| **Deploy** | Vercel (frontend) · HuggingFace (backend) |

---

## Project Structure

```
finora/
├── CLAUDE.md
├── docker-compose.yml
├── finora-backend
│   ├── backend
│   │   ├── api
│   │   │   ├── __init__.py
│   │   │   ├── middleware
│   │   │   │   ├── guardrails.py
│   │   │   │   ├── __init__.py
│   │   │   │   └── rate_limit.py
│   │   │   └── routes
│   │   │       ├── chat.py
│   │   │       ├── health.py
│   │   │       ├── __init__.py
│   │   │       └── stocks.py
│   │   ├── data
│   │   │   ├── eval_results
│   │   │   │   ├── latest.json
│   │   │   │   ├── ragas_20260426.json
│   │   │   │   ├── ragas_20260426_v3.json
│   │   │   │   └── ragas_20260426_v4.json
│   │   │   └── universe
│   │   │       └── stocks.json
│   │   ├── finora_mcp
│   │   │   ├── __init__.py
│   │   │   ├── server.py
│   │   │   └── tools
│   │   │       ├── fundamentals.py
│   │   │       ├── historical.py
│   │   │       ├── __init__.py
│   │   │       ├── news.py
│   │   │       ├── quote.py
│   │   │       └── screener.py
│   │   ├── graph
│   │   │   ├── finora_graph.py
│   │   │   ├── __init__.py
│   │   │   ├── nodes
│   │   │   │   ├── fundamentals_node.py
│   │   │   │   ├── fusion_node.py
│   │   │   │   ├── historical_rag_node.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── intent_classifier.py
│   │   │   │   ├── news_rag_node.py
│   │   │   │   ├── realtime_node.py
│   │   │   │   ├── response_cache.py
│   │   │   │   └── response_node.py
│   │   │   └── state.py
│   │   ├── guardrails
│   │   │   ├── classifier.py
│   │   │   ├── disclaimers.py
│   │   │   ├── __init__.py
│   │   │   └── output_filter.py
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── observability
│   │   │   ├── __init__.py
│   │   │   ├── langsmith_client.py
│   │   │   ├── langsmith_url.py
│   │   │   └── metrics.py
│   │   ├── rag
│   │   │   ├── chunking
│   │   │   │   ├── financial.py
│   │   │   │   ├── __init__.py
│   │   │   │   └── strategies.py
│   │   │   ├── embedder.py
│   │   │   ├── evaluation
│   │   │   │   ├── __init__.py
│   │   │   │   ├── ragas_eval.py
│   │   │   │   └── synthetic.py
│   │   │   ├── ingestion
│   │   │   │   ├── collections.py
│   │   │   │   ├── filings.py
│   │   │   │   ├── historical.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── news.py
│   │   │   │   ├── scheduler.py
│   │   │   │   └── universe.py
│   │   │   ├── __init__.py
│   │   │   ├── pipeline.py
│   │   │   ├── retrieval
│   │   │   │   ├── deduplication.py
│   │   │   │   ├── hybrid.py
│   │   │   │   ├── hyde.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── reranker.py
│   │   │   │   └── router.py
│   │   │   └── yahoo_client.py
│   │   └── scripts
│   │       ├── build_universe.py
│   │       ├── eval_rag.py
│   │       └── ingest_filings.py
│   │       ├── ingest_historical.py
│   │       └── ingest_news.py
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── .env
│   ├── .env.example
│   ├── .gitignore
│   ├── README.md
│   ├── requirements-dev.txt
│   └── requirements.txt
├── finora-frontend
│   ├── app
│   │   ├── api
│   │   │   ├── chat
│   │   │   │   └── route.ts
│   │   │   └── stocks
│   │   │       └── [ticker]
│   │   │           └── ohlcv
│   │   │               └── route.ts
│   │   ├── dashboard
│   │   │   ├── page.tsx
│   │   │   └── [ticker]
│   │   │       ├── error.tsx
│   │   │       ├── loading.tsx
│   │   │       └── page.tsx
│   │   ├── eval
│   │   │   └── page.tsx
│   │   ├── icon.svg
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── providers.tsx
│   ├── components
│   │   ├── chat
│   │   │   ├── ChatInput.tsx
│   │   │   ├── ChatMessage.tsx
│   │   │   ├── ChatWidget.tsx
│   │   │   ├── StockSummaryCard.tsx
│   │   │   ├── SuggestionChips.tsx
│   │   │   └── TypingIndicator.tsx
│   │   ├── dashboard
│   │   │   ├── AnalystConsensus.tsx
│   │   │   ├── FundamentalsGrid.tsx
│   │   │   ├── HistoricalRagPanel.tsx
│   │   │   ├── NewsRagPanel.tsx
│   │   │   ├── PriceChart.tsx
│   │   │   ├── SectorHeatmap.tsx
│   │   │   ├── SimilarStocks.tsx
│   │   │   ├── StockAbout.tsx
│   │   │   ├── StockHeader.tsx
│   │   │   └── StockSearch.tsx
│   │   ├── landing
│   │   │   ├── Features.tsx
│   │   │   ├── Footer.tsx
│   │   │   ├── Hero.tsx
│   │   │   ├── MarketPulse.tsx
│   │   │   └── Navbar.tsx
│   │   └── ui
│   │       ├── badge.tsx
│   │       ├── command.tsx
│   │       ├── FinoraIcon.tsx
│   │       ├── skeleton.tsx
│   │       ├── sparkline.tsx
│   │       ├── StockLogo.tsx
│   │       ├── ThemeToggle.tsx
│   │       └── TickerTape.tsx
│   ├── components.json
│   ├── Dockerfile
│   ├── .env
│   ├── .env.example
│   ├── jest.config.js
│   ├── lib
│   │   ├── api.ts
│   │   ├── format.ts
│   │   ├── streaming.ts
│   │   ├── theme-context.tsx
│   │   ├── universe.ts
│   │   └── utils.ts
│   ├── next.config.mjs
│   ├── next-env.d.ts
│   ├── package.json
│   ├── package-lock.json
│   ├── postcss.config.mjs
│   ├── public
│   │   ├── architecture.png
│   │   ├── finora_icon.png
│   │   └── finora_logo.png
│   ├── styles
│   │   └── globals.css
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── tsconfig.tsbuildinfo
├── .gitignore
├── README.md
└── tests
    ├── backend
    │   ├── conftest.py
    │   ├── integration
    │   │   └── test_pipeline.py
    │   ├── stress
    │   │   ├── queries.py
    │   │   └── test_suite.py
    │   └── unit
    │       ├── test_fusion_signals.py
    │       ├── test_guardrails.py
    │       └── test_intent_classifier.py
    ├── frontend
    │   └── __tests__
    │       └── streaming.test.ts
    └── README.md
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
python backend/scripts/build_universe.py

# Seed historical RAG data (~30 min for full list)
python backend/scripts/ingest_historical.py --tickers AAPL MSFT NVDA RELIANCE TCS INFY --years 20

# Seed news corpus
python backend/scripts/ingest_news.py --tickers AAPL MSFT NVDA RELIANCE TCS INFY

# Seed filings
python backend/scripts/ingest_filings.py --tickers AAPL MSFT NVDA RELIANCE TCS INFY

# Start backend
uvicorn backend.main:app --reload --port 7860
```

### 3. Frontend

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

### finora-backend → Hugging Face Spaces

1. Create a new **Docker Space** for `finora-backend`.
2. Add this to the top of the backend `README.md` in the Space repo:

```yaml
***
title: finora-backend
emoji: 🚀
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
***
```

3. Make sure your backend container starts on `0.0.0.0:7860`.

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 7860
```

4. Set Hugging Face Space variables/secrets for:
- `GROQ_API_KEY`
- `GROQ_MODEL_PRIMARY`
- `GROQ_MODEL_FAST`
- `LANGCHAIN_API_KEY`
- `LANGCHAIN_PROJECT`
- `LANGCHAIN_TRACING_V2`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `GUARDRAILS_ENABLED`
- `DISCLAIMER_LOCALE`
- `CORS_ORIGINS`
- `ENV`

5. After deployment, your Space URL will be something like:

```bash
https://finora-backend.hf.space
```

### Frontend → Vercel

```bash
npm install -g vercel
cd finora-frontend && vercel
vercel env add NEXT_PUBLIC_BACKEND_URL
vercel --prod
```

### Verify

```bash
curl https://<your-space-name>.hf.space/api/health
# → {"status":"ok","qdrant":"connected","groq":"connected","langsmith":"configured","langsmith_url":"https://smith.langchain.com/projects/finora-prod","universe_size":553}
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
python backend/scripts/eval_rag.py --tickers AAPL MSFT RELIANCE.NS --n 5
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
