"use client";

import Link from "next/link";
import { Users, ChevronRight, Globe } from "lucide-react";

interface SimilarStock {
  ticker: string;
  name: string;
  sector: string;
  exchange: string;
  currency: string;
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

function ExchangeBadge({ exchange }: { exchange: string }) {
  const flag = EXCHANGE_FLAG[exchange.toUpperCase()];
  return (
    <span className="inline-flex items-center gap-0.5 text-[9px] font-semibold bg-muted/60 text-muted-foreground px-1.5 py-0.5 rounded border border-border/60">
      {flag ?? <Globe className="w-2.5 h-2.5" />}
      {exchange}
    </span>
  );
}

export function SimilarStocks({ stocks, currentTicker }: Props) {
  if (!stocks.length) return null;

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-muted/30">
        <div className="w-6 h-6 rounded-md bg-primary/10 flex items-center justify-center">
          <Users className="w-3.5 h-3.5 text-primary" />
        </div>
        <h3 className="text-sm font-semibold text-foreground">Similar Stocks</h3>
        <span className="ml-auto text-[10px] font-medium bg-primary/10 text-primary px-2 py-0.5 rounded-full border border-primary/20">
          {stocks.length} peers
        </span>
      </div>

      {/* Stock list */}
      <ul className="divide-y divide-border">
        {stocks.map((s) => (
          <li key={s.ticker}>
            <Link
              href={`/dashboard/${s.ticker}`}
              className="flex items-center gap-3 px-4 py-3 hover:bg-muted/20 transition-colors group"
            >
              {/* Ticker block */}
              <div className="flex-shrink-0 w-14 h-9 rounded-lg bg-muted/40 border border-border/60 flex items-center justify-center group-hover:border-primary/30 group-hover:bg-primary/5 transition-all">
                <span className="font-mono text-[11px] font-bold text-foreground group-hover:text-primary transition-colors leading-none text-center px-1 truncate">
                  {s.ticker.length > 6 ? s.ticker.slice(0, 5) + "…" : s.ticker}
                </span>
              </div>

              {/* Name + exchange */}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-foreground truncate leading-tight">
                  {s.name}
                </p>
                <div className="flex items-center gap-1.5 mt-1">
                  <ExchangeBadge exchange={s.exchange} />
                  {s.sector && (
                    <span className="text-[9px] text-muted-foreground/60 truncate">
                      {s.sector}
                    </span>
                  )}
                </div>
              </div>

              {/* Chevron */}
              <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/30 group-hover:text-primary/60 flex-shrink-0 transition-colors group-hover:translate-x-0.5 transform duration-150" />
            </Link>
          </li>
        ))}
      </ul>

      {/* Footer hint */}
      <div className="px-4 py-2 border-t border-border/50 bg-muted/10">
        <p className="text-[10px] text-muted-foreground/50 text-center">
          Same sector · Click to explore
        </p>
      </div>
    </div>
  );
}
