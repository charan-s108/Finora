"use client";

import { TrendingUp, TrendingDown, Target, BarChart3 } from "lucide-react";
import { StockLogo } from "@/components/ui/StockLogo";
import type { StockDetail } from "@/lib/api";

function fmt(n: number | null | undefined, decimals = 2): string {
  if (n == null) return "—";
  return n.toFixed(decimals);
}

function fmtBig(n: number | null | undefined): string {
  if (n == null) return "—";
  if (Math.abs(n) >= 1e12) return `${(n / 1e12).toFixed(2)}T`;
  if (Math.abs(n) >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  return n.toFixed(0);
}

function fmtPrice(n: number | null | undefined, currency = "USD"): string {
  if (n == null) return "—";
  const sym = currency === "INR" ? "₹" : currency === "GBP" ? "£" : currency === "EUR" ? "€" : "$";
  return `${sym}${n.toFixed(2)}`;
}

interface Props {
  stock: StockDetail;
}

export function StockSummaryCard({ stock }: Props) {
  const isUp = (stock.pct_change ?? 0) >= 0;
  const currency = stock.currency || "USD";
  const consensus = stock.analyst_consensus;
  const totalAnalysts = consensus ? consensus.buy + consensus.hold + consensus.sell : 0;
  const buyPct = totalAnalysts ? Math.round((consensus!.buy / totalAnalysts) * 100) : 0;
  const holdPct = totalAnalysts ? Math.round((consensus!.hold / totalAnalysts) * 100) : 0;
  const sellPct = totalAnalysts ? 100 - buyPct - holdPct : 0;

  const price52High = stock.week_52_high;
  const price52Low = stock.week_52_low;
  const price = stock.price;
  const rangePos =
    price != null && price52High != null && price52Low != null && price52High !== price52Low
      ? Math.max(0, Math.min(100, ((price - price52Low) / (price52High - price52Low)) * 100))
      : null;

  const metrics = [
    { label: "P/E", value: fmt(stock.pe, 1) },
    { label: "Fwd P/E", value: fmt(stock.forward_pe, 1) },
    { label: "EPS", value: stock.eps != null ? fmtPrice(stock.eps, currency) : "—" },
    { label: "Mkt Cap", value: fmtBig(stock.market_cap) },
    { label: "Volume", value: fmtBig(stock.volume) },
    { label: "Avg Vol", value: fmtBig(stock.avg_volume_30d) },
  ];

  return (
    <div className="rounded-xl border border-border bg-card/60 backdrop-blur-sm p-3.5 space-y-3 w-full">
      {/* Finora header */}
      <div className="flex items-center gap-1.5 mb-0.5">
        <div className="w-4 h-4 rounded bg-primary flex items-center justify-center">
          <span className="text-primary-foreground text-[8px] font-bold">F</span>
        </div>
        <span className="text-xs text-muted-foreground font-medium">Finora AI · Live Snapshot</span>
        <div className="ml-auto flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[10px] text-emerald-400">Live</span>
        </div>
      </div>

      {/* Price header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <StockLogo website={stock.website} ticker={stock.ticker} size={32} />
          <div>
            <div className="font-mono font-bold text-foreground text-sm">{stock.ticker}</div>
            {(stock.sector || stock.industry) && (
              <div className="text-[10px] text-muted-foreground mt-0.5 leading-tight">
                {[stock.sector, stock.industry].filter(Boolean).join(" · ")}
              </div>
            )}
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-semibold font-mono text-foreground leading-none">
            {fmtPrice(stock.price, currency)}
          </div>
          <div
            className={`text-xs font-medium flex items-center justify-end gap-0.5 mt-0.5 ${
              isUp ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {isUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {isUp && stock.change != null ? "+" : ""}
            {fmt(stock.change)} ({isUp ? "+" : ""}
            {fmt(stock.pct_change)}%)
          </div>
        </div>
      </div>

      {/* 52W range */}
      {rangePos !== null && (
        <div className="space-y-1">
          <div className="flex justify-between text-[10px] text-muted-foreground">
            <span>52W Low: {fmtPrice(price52Low, currency)}</span>
            <span>52W High: {fmtPrice(price52High, currency)}</span>
          </div>
          <div className="relative h-1.5 rounded-full overflow-hidden bg-secondary">
            <div
              className="absolute inset-y-0 left-0 right-0 rounded-full"
              style={{
                background: "linear-gradient(to right, #ef4444, #eab308, #22c55e)",
              }}
            />
            <div
              className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-white border-2 border-primary shadow-md"
              style={{ left: `calc(${rangePos}% - 6px)` }}
            />
          </div>
        </div>
      )}

      {/* Metrics grid */}
      <div className="grid grid-cols-3 gap-1.5">
        {metrics.map(({ label, value }) => (
          <div
            key={label}
            className="bg-secondary/40 rounded-lg px-2 py-1.5 text-center border border-border/30"
          >
            <div className="text-[10px] text-muted-foreground leading-none mb-0.5">{label}</div>
            <div className="text-xs font-mono font-semibold text-foreground">{value}</div>
          </div>
        ))}
      </div>

      {/* Analyst consensus */}
      {consensus && totalAnalysts > 0 && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <Target className="w-3 h-3" />
              <span>Analyst Consensus · {totalAnalysts} analysts</span>
            </div>
            {consensus.avg_target != null && (
              <span className="text-[10px] text-muted-foreground">
                Target: {fmtPrice(consensus.avg_target, currency)}
              </span>
            )}
          </div>
          <div className="flex h-2 rounded-full overflow-hidden gap-px">
            {buyPct > 0 && (
              <div className="bg-emerald-500 transition-all" style={{ width: `${buyPct}%` }} />
            )}
            {holdPct > 0 && (
              <div className="bg-yellow-400 transition-all" style={{ width: `${holdPct}%` }} />
            )}
            {sellPct > 0 && (
              <div className="bg-red-500 transition-all" style={{ width: `${sellPct}%` }} />
            )}
          </div>
          <div className="flex justify-between text-[10px]">
            <span className="text-emerald-400 font-medium">{consensus.buy} Buy ({buyPct}%)</span>
            <span className="text-yellow-400 font-medium">{consensus.hold} Hold</span>
            <span className="text-red-400 font-medium">{consensus.sell} Sell</span>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center gap-1.5 pt-0.5 border-t border-border/30">
        <BarChart3 className="w-3 h-3 text-muted-foreground" />
        <span className="text-[10px] text-muted-foreground">
          Ask me anything about {stock.ticker} — news, history, fundamentals
        </span>
      </div>
    </div>
  );
}
