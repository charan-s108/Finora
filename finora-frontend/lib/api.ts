import { z } from "zod";

const BACKEND = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:7860";

// ── Schemas ────────────────────────────────────────────────────────────────

export const StockSearchResultSchema = z.object({
  ticker: z.string(),
  name: z.string(),
  exchange: z.string(),
  sector: z.string().nullable().optional(),
  country: z.string().nullable().optional(),
  yf_ticker: z.string().optional(),
});
export type StockSearchResult = z.infer<typeof StockSearchResultSchema>;

export const AnalystConsensusSchema = z.object({
  buy: z.number(),
  hold: z.number(),
  sell: z.number(),
  avg_target: z.number().nullable().optional(),
});

export const NewsItemSchema = z.object({
  text: z.string(),
  title: z.string(),
  source: z.string(),
  published_at: z.string(),
  url: z.string(),
});

export const HistoricalSignalSchema = z.object({
  text: z.string(),
  event_type: z.string(),
  date_range: z.string(),
  return_pct: z.number().nullable().optional(),
});

export const FinancialPeriodSchema = z.object({
  period: z.string(),
  period_type: z.string(),
  revenue: z.number().nullable().optional(),
  net_income: z.number().nullable().optional(),
  revenue_growth_pct: z.number().nullable().optional(),
  profit_growth_pct: z.number().nullable().optional(),
});
export type FinancialPeriod = z.infer<typeof FinancialPeriodSchema>;

export const FinancialPerformanceSchema = z.object({
  currency: z.string(),
  currency_unit: z.string(),
  annual: z.array(FinancialPeriodSchema),
  quarterly: z.array(FinancialPeriodSchema),
  revenue_1y_growth: z.number().nullable().optional(),
  profit_1y_growth: z.number().nullable().optional(),
  revenue_3y_cagr: z.number().nullable().optional(),
  profit_3y_cagr: z.number().nullable().optional(),
});
export type FinancialPerformance = z.infer<typeof FinancialPerformanceSchema>;

export const FinancialsDetailSchema = z.object({
  ticker: z.string(),
  currency: z.string(),
  currency_unit: z.string(),
  income_annual: z.array(z.record(z.unknown())),
  income_quarterly: z.array(z.record(z.unknown())),
  balance_sheet: z.array(z.record(z.unknown())),
  cashflow: z.array(z.record(z.unknown())),
});
export type FinancialsDetail = z.infer<typeof FinancialsDetailSchema>;

export const StockDetailSchema = z.object({
  ticker: z.string(),
  name: z.string().nullable().optional(),
  exchange: z.string().optional(),
  currency: z.string().optional(),
  sector: z.string().nullable().optional(),
  industry: z.string().nullable().optional(),
  country: z.string().nullable().optional(),
  city: z.string().nullable().optional(),
  website: z.string().nullable().optional(),
  full_time_employees: z.number().nullable().optional(),
  business_summary: z.string().nullable().optional(),
  beta: z.number().nullable().optional(),
  dividend_yield: z.number().nullable().optional(),
  price: z.number().nullable().optional(),
  change: z.number().nullable().optional(),
  pct_change: z.number().nullable().optional(),
  volume: z.number().nullable().optional(),
  avg_volume_30d: z.number().nullable().optional(),
  market_cap: z.number().nullable().optional(),
  pe: z.number().nullable().optional(),
  forward_pe: z.number().nullable().optional(),
  eps: z.number().nullable().optional(),
  week_52_high: z.number().nullable().optional(),
  week_52_low: z.number().nullable().optional(),
  analyst_consensus: AnalystConsensusSchema.nullable().optional(),
  ohlcv_7d: z.array(z.object({
    date: z.string(),
    open: z.number(),
    high: z.number(),
    low: z.number(),
    close: z.number(),
    volume: z.number(),
  })).optional(),
  news_rag: z.array(NewsItemSchema).optional(),
  historical_signals: z.array(HistoricalSignalSchema).optional(),
  similar_stocks: z.array(z.object({
    ticker: z.string(),
    name: z.string(),
    sector: z.string(),
    exchange: z.string(),
    currency: z.string(),
    website: z.string().nullable().optional(),
  })).optional(),
  financial_performance: FinancialPerformanceSchema.nullable().optional(),
});
export type StockDetail = z.infer<typeof StockDetailSchema>;

export const SectorDataSchema = z.object({
  sector: z.string(),
  etf: z.string(),
  return_pct: z.number(),
  price: z.number().nullable().optional(),
});
export type SectorData = z.infer<typeof SectorDataSchema>;

// ── Fetch helpers ──────────────────────────────────────────────────────────

export async function searchStocks(query: string, limit = 10): Promise<StockSearchResult[]> {
  const res = await fetch(`${BACKEND}/api/stocks/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  if (!res.ok) return [];
  const data = await res.json();
  return z.array(StockSearchResultSchema).parse(data);
}

export async function getStockDetail(ticker: string): Promise<StockDetail | null> {
  const res = await fetch(`${BACKEND}/api/stocks/${encodeURIComponent(ticker)}`, {
    cache: "no-store",
  });
  if (!res.ok) return null;
  const data = await res.json();
  return StockDetailSchema.parse(data);
}

export type OHLCVTimeframe = "1D" | "1W" | "1M" | "3M" | "6M" | "1Y" | "3Y" | "5Y" | "ALL";

export const OHLCVBarSchema = z.object({
  date: z.string(),
  open: z.number(),
  high: z.number(),
  low: z.number(),
  close: z.number(),
  volume: z.number(),
});
export type OHLCVBar = z.infer<typeof OHLCVBarSchema>;

export async function getOHLCV(ticker: string, range: OHLCVTimeframe = "1M"): Promise<OHLCVBar[]> {
  const res = await fetch(`${BACKEND}/api/stocks/${encodeURIComponent(ticker)}/ohlcv?range=${range}`);
  if (!res.ok) return [];
  const data = await res.json();
  return z.array(OHLCVBarSchema).parse(data.bars ?? []);
}

export async function getFinancials(ticker: string): Promise<FinancialsDetail | null> {
  try {
    const res = await fetch(`${BACKEND}/api/stocks/${encodeURIComponent(ticker)}/financials`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return FinancialsDetailSchema.parse(await res.json());
  } catch {
    return null;
  }
}

export async function getSectors(): Promise<SectorData[]> {
  try {
    const res = await fetch(`${BACKEND}/api/stocks/sectors`, { next: { revalidate: 300 } });
    if (!res.ok) return [];
    const data = await res.json();
    return z.array(SectorDataSchema).parse(data);
  } catch {
    return [];
  }
}

export async function getHealth(): Promise<Record<string, unknown>> {
  const res = await fetch(`${BACKEND}/api/health`);
  return res.json();
}

export const EvalMetricSchema = z.object({
  score: z.number(),
  target: z.number(),
  passed: z.boolean(),
  delta: z.number().optional(),
});

export const EvalResponseSchema = z.object({
  overall_pass: z.boolean(),
  scores: z.record(z.number()),
  results: z.record(EvalMetricSchema),
  run_at: z.string().nullable().optional(),
  tickers: z.array(z.string()).optional(),
  n_pairs: z.number().optional(),
});
export type EvalResponse = z.infer<typeof EvalResponseSchema>;

export async function getEvalResults(): Promise<EvalResponse | null> {
  try {
    const res = await fetch(`${BACKEND}/api/eval/latest`, { cache: "no-store" });
    if (!res.ok) return null;
    return EvalResponseSchema.parse(await res.json());
  } catch {
    return null;
  }
}
