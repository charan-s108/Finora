"use client";

import { LayoutGrid } from "lucide-react";
import type { SectorData } from "@/lib/api";

interface Props {
  data?: SectorData[];
}

const MOCK_SECTORS: SectorData[] = [
  { sector: "Technology",      etf: "XLK",  return_pct: 1.4,  price: 205.32 },
  { sector: "Healthcare",      etf: "XLV",  return_pct: -0.8, price: 138.20 },
  { sector: "Financials",      etf: "XLF",  return_pct: 0.6,  price: 43.10 },
  { sector: "Energy",          etf: "XLE",  return_pct: -1.2, price: 87.54 },
  { sector: "Consumer Disc.",  etf: "XLY",  return_pct: 0.3,  price: 192.80 },
  { sector: "Consumer Staples",etf: "XLP",  return_pct: -0.3, price: 76.40 },
  { sector: "Materials",       etf: "XLB",  return_pct: -0.5, price: 88.60 },
  { sector: "Industrials",     etf: "XLI",  return_pct: 0.9,  price: 131.20 },
  { sector: "Utilities",       etf: "XLU",  return_pct: -0.2, price: 68.90 },
  { sector: "Real Estate",     etf: "XLRE", return_pct: 0.4,  price: 38.72 },
  { sector: "Comm. Services",  etf: "XLC",  return_pct: 1.1,  price: 88.14 },
  { sector: "Semiconductors",  etf: "SOXX", return_pct: 2.1,  price: 218.60 },
];

const SECTOR_SHORT: Record<string, string> = {
  "Technology":       "Tech",
  "Healthcare":       "Health",
  "Financials":       "Finance",
  "Energy":           "Energy",
  "Consumer Disc.":   "Cons Disc",
  "Consumer Staples": "Staples",
  "Materials":        "Material",
  "Industrials":      "Industrl",
  "Utilities":        "Utilities",
  "Real Estate":      "Real Est",
  "Comm. Services":   "Comm Svc",
  "Semiconductors":   "Semicon",
};

function pctToClasses(pct: number): { bg: string; text: string; bar: string } {
  if (pct >= 2.0)  return { bg: "bg-emerald-500/80 border-emerald-400/30", text: "text-emerald-50",   bar: "bg-emerald-400" };
  if (pct >= 1.0)  return { bg: "bg-emerald-500/45 border-emerald-400/20", text: "text-emerald-200",  bar: "bg-emerald-500" };
  if (pct > 0)     return { bg: "bg-emerald-500/18 border-emerald-400/15", text: "text-emerald-300",  bar: "bg-emerald-600" };
  if (pct > -1.0)  return { bg: "bg-rose-500/18 border-rose-400/15",       text: "text-rose-300",     bar: "bg-rose-600" };
  if (pct > -2.0)  return { bg: "bg-rose-500/45 border-rose-400/20",       text: "text-rose-200",     bar: "bg-rose-500" };
  return           { bg: "bg-rose-500/80 border-rose-400/30",              text: "text-rose-50",      bar: "bg-rose-400" };
}

export function SectorHeatmap({ data }: Props) {
  const isLive = Boolean(data?.length);
  const sectors = isLive ? data! : MOCK_SECTORS;
  const sorted = [...sectors].sort((a, b) => b.return_pct - a.return_pct);
  const best  = sorted[0];
  const worst = sorted[sorted.length - 1];

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-muted/30">
        <div className="w-6 h-6 rounded-md bg-primary/10 flex items-center justify-center">
          <LayoutGrid className="w-3.5 h-3.5 text-primary" />
        </div>
        <h3 className="text-sm font-semibold text-foreground">Sector Performance</h3>
        <div className="ml-auto flex items-center gap-2">
          {isLive ? (
            <span className="inline-flex items-center gap-1 text-[10px] font-medium bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live
            </span>
          ) : (
            <span className="text-[10px] text-muted-foreground/50 font-medium">sample</span>
          )}
        </div>
      </div>

      {/* Best/Worst strip */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border/50 bg-muted/10">
        <div className="flex items-center gap-1.5 text-[10px]">
          <span className="text-muted-foreground">Best:</span>
          <span className="font-mono font-bold text-emerald-400">{best.etf}</span>
          <span className="text-emerald-400 font-semibold">{best.return_pct >= 0 ? "+" : ""}{best.return_pct.toFixed(2)}%</span>
        </div>
        <span className="text-border">·</span>
        <div className="flex items-center gap-1.5 text-[10px]">
          <span className="text-muted-foreground">Worst:</span>
          <span className="font-mono font-bold text-rose-400">{worst.etf}</span>
          <span className="text-rose-400 font-semibold">{worst.return_pct >= 0 ? "+" : ""}{worst.return_pct.toFixed(2)}%</span>
        </div>
      </div>

      {/* 3-column × 4-row heatmap */}
      <div className="p-3 grid grid-cols-3 gap-1.5">
        {sectors.map((s) => {
          const { bg, text, bar } = pctToClasses(s.return_pct);
          const shortName = SECTOR_SHORT[s.sector] ?? s.sector.slice(0, 8);
          const isPositive = s.return_pct >= 0;

          return (
            <div
              key={s.sector}
              className={`relative rounded-lg border p-2.5 flex flex-col gap-0.5 overflow-hidden transition-transform hover:scale-[1.02] ${bg}`}
              title={`${s.sector} (${s.etf}): ${isPositive ? "+" : ""}${s.return_pct.toFixed(2)}%`}
            >
              {/* Intensity bar along bottom */}
              <div className={`absolute bottom-0 left-0 right-0 h-0.5 opacity-60 ${bar}`} />

              <span className={`text-[10px] font-semibold leading-tight truncate ${text}`}>
                {shortName}
              </span>
              <span className={`text-[9px] font-medium opacity-70 ${text}`}>
                {s.etf}
              </span>
              <span className={`text-xs font-bold font-mono mt-0.5 ${text}`}>
                {isPositive ? "+" : ""}{s.return_pct.toFixed(2)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
