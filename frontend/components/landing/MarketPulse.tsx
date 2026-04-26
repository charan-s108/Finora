"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer,
} from "recharts";
import { TrendingUp, TrendingDown, ChevronDown, ArrowUpRight } from "lucide-react";
import { getOHLCV } from "@/lib/api";
import type { OHLCVBar } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

// Interleaved US + India — globally representative from page 1
const TABLE_TICKERS = [
  { ticker: "AAPL",      label: "Apple",                 exchange: "NASDAQ", currency: "USD" },
  { ticker: "RELIANCE",  label: "Reliance Industries",   exchange: "NSE",    currency: "INR" },
  { ticker: "MSFT",      label: "Microsoft",             exchange: "NASDAQ", currency: "USD" },
  { ticker: "TCS",       label: "Tata Consultancy",      exchange: "NSE",    currency: "INR" },
  { ticker: "NVDA",      label: "NVIDIA",                exchange: "NASDAQ", currency: "USD" },
  { ticker: "HDFCBANK",  label: "HDFC Bank",             exchange: "NSE",    currency: "INR" },
  { ticker: "GOOGL",     label: "Alphabet",              exchange: "NASDAQ", currency: "USD" },
  { ticker: "INFY",      label: "Infosys",               exchange: "NSE",    currency: "INR" },
  { ticker: "AMZN",      label: "Amazon",                exchange: "NASDAQ", currency: "USD" },
  { ticker: "ICICIBANK", label: "ICICI Bank",            exchange: "NSE",    currency: "INR" },
  { ticker: "META",      label: "Meta Platforms",        exchange: "NASDAQ", currency: "USD" },
  { ticker: "WIPRO",     label: "Wipro",                 exchange: "NSE",    currency: "INR" },
  { ticker: "TSLA",      label: "Tesla",                 exchange: "NASDAQ", currency: "USD" },
  { ticker: "LT",        label: "Larsen & Toubro",       exchange: "NSE",    currency: "INR" },
  { ticker: "JPM",       label: "JPMorgan Chase",        exchange: "NYSE",   currency: "USD" },
];

const PAGE_SIZE = 5;
const FEATURED_TICKER = "AAPL";

interface Row {
  ticker: string;
  label: string;
  exchange: string;
  currency: string;
  price: number;
  pct_change: number;
}

// Module-level cache so rows survive navigation
const _rowCache: Map<string, Row> = new Map();

async function fetchRow(s: typeof TABLE_TICKERS[0]): Promise<Row | null> {
  if (_rowCache.has(s.ticker)) return _rowCache.get(s.ticker)!;
  try {
    const res = await fetch(`/api/stocks/${encodeURIComponent(s.ticker)}`);
    if (!res.ok) return null;
    const d = await res.json();
    if (d.price == null) return null;
    const row: Row = {
      ticker: s.ticker,
      label: s.label,
      exchange: s.exchange,
      currency: s.currency,
      price: d.price,
      pct_change: d.pct_change ?? 0,
    };
    _rowCache.set(s.ticker, row);
    return row;
  } catch {
    return null;
  }
}

function BigChart({
  ticker, bars, loading,
}: { ticker: string; bars: OHLCVBar[]; loading: boolean }) {
  const data = bars.map((b) => ({ date: b.date.slice(5), close: b.close }));
  const closes = data.map((d) => d.close);
  const isUp = closes.length >= 2 ? closes[closes.length - 1] >= closes[0] : true;
  const color = isUp ? "#10b981" : "#ef4444";
  const min = closes.length ? Math.min(...closes) : 0;
  const max = closes.length ? Math.max(...closes) : 1;
  const pad = (max - min) * 0.08 || 1;

  if (loading) {
    return (
      <div className="h-[280px] flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="bigChartGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.25} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
        <XAxis
          dataKey="date" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false} tickLine={false} interval="preserveStartEnd"
        />
        <YAxis
          domain={[min - pad, max + pad]}
          tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false} tickLine={false} width={56}
          tickFormatter={(v) => `$${v >= 1000 ? (v / 1000).toFixed(1) + "k" : v.toFixed(0)}`}
        />
        <Tooltip
          contentStyle={{
            background: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            borderRadius: 8, fontSize: 12,
          }}
          labelStyle={{ color: "hsl(var(--muted-foreground))" }}
          itemStyle={{ color }}
          formatter={(v: number) => [`$${v.toFixed(2)}`, ticker]}
        />
        <Area
          type="monotone" dataKey="close"
          stroke={color} strokeWidth={2}
          fill="url(#bigChartGrad)" dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function RowSkeleton() {
  return (
    <div className="flex items-center gap-4 px-4 py-3 animate-pulse border-b border-border last:border-0">
      <div className="flex-1 space-y-1.5">
        <div className="h-3 w-20 bg-muted rounded" />
        <div className="h-2 w-32 bg-muted/50 rounded" />
      </div>
      <div className="h-3 w-16 bg-muted rounded" />
      <div className="h-3 w-12 bg-muted/60 rounded" />
    </div>
  );
}

export function MarketPulse() {
  const router = useRouter();

  // Big chart state
  const [featured, setFeatured] = useState(FEATURED_TICKER);
  const [chartBars, setChartBars] = useState<OHLCVBar[]>([]);
  const [chartLoading, setChartLoading] = useState(true);

  // Table state
  const [rows, setRows] = useState<Row[]>([]);
  const [page, setPage] = useState(1);
  const [tableLoading, setTableLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const initRef = useRef(false);

  // Load big chart
  const loadChart = useCallback(async (ticker: string) => {
    setChartLoading(true);
    try {
      const bars = await getOHLCV(ticker, "1M");
      setChartBars(bars);
    } catch { setChartBars([]); }
    finally { setChartLoading(false); }
  }, []);

  useEffect(() => { loadChart(featured); }, [featured, loadChart]);

  // Load first page once — ref guard prevents StrictMode double-fire
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;
    loadPage(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadPage(p: number) {
    setTableLoading(true);
    const slice = TABLE_TICKERS.slice((p - 1) * PAGE_SIZE, p * PAGE_SIZE);
    const results = await Promise.allSettled(slice.map(fetchRow));
    const valid = results
      .filter((r): r is PromiseFulfilledResult<Row | null> => r.status === "fulfilled")
      .map((r) => r.value)
      .filter((v): v is Row => v !== null);
    setRows((prev) => [...prev, ...valid]);
    setHasMore(p * PAGE_SIZE < TABLE_TICKERS.length);
    setPage(p);
    setTableLoading(false);
  }

  const featuredRow = rows.find((r) => r.ticker === featured);
  const chartUp = featuredRow ? featuredRow.pct_change >= 0 : true;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
      {/* Big chart — left, 3/5 width */}
      <div className="lg:col-span-3 rounded-2xl border border-border bg-card overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wide mb-0.5">
              Featured · 30-Day
            </p>
            <div className="flex items-center gap-3">
              <span className="font-heading font-bold text-xl text-foreground">{featured}</span>
              {featuredRow && (
                <>
                  <span className="text-sm font-semibold text-foreground">
                    {formatCurrency(featuredRow.price, featuredRow.currency)}
                  </span>
                  <span className={`text-sm font-semibold flex items-center gap-0.5 ${chartUp ? "text-emerald-500" : "text-rose-500"}`}>
                    {chartUp ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                    {chartUp ? "+" : ""}{featuredRow.pct_change.toFixed(2)}%
                  </span>
                </>
              )}
            </div>
          </div>
          <button
            onClick={() => router.push(`/dashboard/${featured}`)}
            className="flex items-center gap-1.5 text-xs text-primary hover:underline font-medium"
          >
            Deep dive <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="p-4">
          <BigChart ticker={featured} bars={chartBars} loading={chartLoading} />
        </div>
      </div>

      {/* Table — right, 2/5 width */}
      <div className="lg:col-span-2 rounded-2xl border border-border bg-card overflow-hidden flex flex-col">
        <div className="px-5 py-4 border-b border-border">
          <p className="font-heading font-semibold text-sm text-foreground">Top Stocks</p>
          <p className="text-xs text-muted-foreground">Click to view · row to chart</p>
        </div>

        <div className="flex-1 divide-y divide-border">
          {rows.map((row) => {
            const up = row.pct_change >= 0;
            const color = up ? "text-emerald-500" : "text-rose-500";
            const isFeatured = row.ticker === featured;

            return (
              <div
                key={row.ticker}
                className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-muted/40 ${isFeatured ? "bg-primary/5 border-l-2 border-primary" : ""}`}
                onClick={() => {
                  setFeatured(row.ticker);
                  loadChart(row.ticker);
                }}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono font-bold text-sm text-foreground">{row.ticker}</span>
                    <span className="text-[10px] bg-muted text-muted-foreground px-1.5 py-0.5 rounded">
                      {row.exchange}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground truncate">{row.label}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-sm font-semibold text-foreground">
                    {formatCurrency(row.price, row.currency)}
                  </p>
                  <p className={`text-xs font-semibold ${color} flex items-center justify-end gap-0.5`}>
                    {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    {up ? "+" : ""}{row.pct_change.toFixed(2)}%
                  </p>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); router.push(`/dashboard/${row.ticker}`); }}
                  className="p-1.5 rounded-lg hover:bg-primary/10 transition-colors text-muted-foreground hover:text-primary flex-shrink-0"
                  title={`Open ${row.ticker}`}
                >
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })}

          {tableLoading && Array.from({ length: PAGE_SIZE }).map((_, i) => (
            <RowSkeleton key={i} />
          ))}
        </div>

        {hasMore && !tableLoading && (
          <div className="p-3 border-t border-border">
            <button
              onClick={() => loadPage(page + 1)}
              className="w-full flex items-center justify-center gap-2 py-2 rounded-xl text-sm font-medium text-primary hover:bg-primary/8 transition-colors border border-primary/20 hover:border-primary/40"
            >
              <ChevronDown className="w-4 h-4" />
              Show 5 more stocks
            </button>
          </div>
        )}

        {!hasMore && rows.length > 0 && (
          <div className="p-3 border-t border-border text-center text-xs text-muted-foreground">
            All {rows.length} stocks loaded
          </div>
        )}
      </div>
    </div>
  );
}
