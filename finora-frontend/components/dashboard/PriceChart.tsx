"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  AreaChart,
  Area,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { getOHLCV, type OHLCVBar, type OHLCVTimeframe } from "@/lib/api";
import { currencySymbol } from "@/lib/format";

const TIMEFRAMES: OHLCVTimeframe[] = ["1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "5Y", "ALL"];

interface Props {
  ticker: string;
  currency?: string;
  initialData?: OHLCVBar[];
}

function formatDate(date: string, range: OHLCVTimeframe): string {
  if (range === "1D") {
    // date is a full ISO timestamp — show HH:MM
    const d = new Date(date);
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
  }
  if (range === "1W" || range === "1M") return date.slice(5); // MM-DD
  if (range === "ALL") return date.slice(0, 7); // YYYY-MM
  return date.slice(2); // YY-MM-DD
}

export function PriceChart({ ticker, currency = "USD", initialData }: Props) {
  const [range, setRange] = useState<OHLCVTimeframe>("1M");
  const [bars, setBars] = useState<OHLCVBar[]>(initialData ?? []);
  const [loading, setLoading] = useState(!initialData);
  const sym = currencySymbol(currency);

  const load = useCallback(
    async (r: OHLCVTimeframe) => {
      setLoading(true);
      try {
        const data = await getOHLCV(ticker, r);
        setBars(data);
      } catch {
        setBars([]);
      } finally {
        setLoading(false);
      }
    },
    [ticker]
  );

  useEffect(() => {
    load(range);
  }, [range, load]);

  const data = bars.map((d) => ({
    date: formatDate(d.date, range),
    close: d.close,
    volume: d.volume,
    positive: d.close >= d.open,
  }));

  const closes = data.map((d) => d.close).filter(Boolean);
  const minClose = closes.length ? Math.min(...closes) : 0;
  const maxClose = closes.length ? Math.max(...closes) : 1;
  const pad = (maxClose - minClose) * 0.08 || 1;
  const isUp = closes.length >= 2 ? closes[closes.length - 1] >= closes[0] : true;
  const lineColor = isUp ? "#10b981" : "#ef4444";
  const gradId = `priceGrad_${ticker}`;

  return (
    <div className="card-dark p-4 space-y-3">
      {/* Header + timeframe buttons */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-foreground">Price Chart</h3>
          <span className="text-xs text-muted-foreground font-mono">{ticker}</span>
        </div>
        <div className="flex items-center gap-0.5 bg-secondary/50 rounded-lg p-0.5">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setRange(tf)}
              className={`px-2 py-1 text-[10px] font-medium rounded-md transition-all ${
                range === tf
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="h-[160px] flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      ) : data.length === 0 ? (
        <div className="h-[160px] flex items-center justify-center">
          <span className="text-xs text-muted-foreground">No data for {range}</span>
        </div>
      ) : (
        <>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: 0 }}>
              <defs>
                <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={lineColor} stopOpacity={0.2} />
                  <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
                vertical={false}
              />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[minClose - pad, maxClose + pad]}
                tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                axisLine={false}
                tickLine={false}
                width={60}
                tickFormatter={(v) => `${sym}${v >= 1000 ? (v / 1000).toFixed(1) + "k" : v.toFixed(v >= 100 ? 0 : 2)}`}
              />
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ color: "hsl(var(--muted-foreground))" }}
                itemStyle={{ color: lineColor }}
                formatter={(v: number) => [`${sym}${v.toFixed(2)}`, "Price"]}
              />
              <Area
                type="monotone"
                dataKey="close"
                stroke={lineColor}
                strokeWidth={2}
                fill={`url(#${gradId})`}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>

          {/* Volume bars */}
          <ResponsiveContainer width="100%" height={36}>
            <ComposedChart data={data} margin={{ top: 0, right: 4, bottom: 0, left: 0 }}>
              <Bar dataKey="volume" fill="hsl(var(--muted))" radius={[2, 2, 0, 0]} opacity={0.7} />
              <XAxis dataKey="date" hide />
              <YAxis hide />
            </ComposedChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  );
}
