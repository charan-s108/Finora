"use client";

import Link from "next/link";
import { Globe } from "lucide-react";
import { StockLogo } from "@/components/ui/StockLogo";

interface SimilarStock {
  ticker: string;
  name: string;
  sector: string;
  exchange: string;
  currency: string;
  website?: string | null;
}

interface Props {
  stocks: SimilarStock[];
  currentTicker: string;
}

const EXCHANGE_FLAG: Record<string, string> = {
  NSE: "🇮🇳",
  BSE: "🇮🇳",
  NASDAQ: "🇺🇸",
  NYSE: "🇺🇸",
  TSX: "🇨🇦",
  LSE: "🇬🇧",
};

export function SimilarStocks({ stocks, currentTicker }: Props) {
  if (!stocks.length) return null;

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/20">
        <h3 className="text-sm font-semibold text-foreground">Similar Stocks</h3>
        <span className="text-[10px] font-medium bg-primary/10 text-primary px-2 py-0.5 rounded-full border border-primary/20">
          {stocks.length} peers
        </span>
      </div>

      <div className="p-3 grid grid-cols-3 sm:grid-cols-5 gap-2">
        {stocks.map((s) => {
          const flag = EXCHANGE_FLAG[s.exchange?.toUpperCase() ?? ""];
          const shortTicker = s.ticker.length > 7 ? s.ticker.slice(0, 6) + "…" : s.ticker;
          return (
            <Link
              key={s.ticker}
              href={`/dashboard/${s.ticker}`}
              className="group flex flex-col items-center gap-1.5 p-2 sm:p-2.5 rounded-lg border border-border/60 bg-muted/20 hover:bg-primary/5 hover:border-primary/30 transition-all text-center"
            >
              <StockLogo
                ticker={s.ticker}
                website={s.website}
                exchange={s.exchange}
                size={36}
                className="group-hover:ring-1 group-hover:ring-primary/30 transition-all"
              />
              <p className="text-[9px] sm:text-[10px] font-mono font-semibold text-foreground group-hover:text-primary transition-colors leading-none truncate w-full text-center">
                {shortTicker}
              </p>
              <p className="text-[9px] text-muted-foreground leading-tight line-clamp-2 w-full hidden sm:block">
                {s.name}
              </p>
              <span className="inline-flex items-center gap-0.5 text-[9px] font-medium text-muted-foreground/70">
                {flag ? flag : <Globe className="w-2.5 h-2.5" />}
                <span className="hidden sm:inline">{s.exchange}</span>
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
