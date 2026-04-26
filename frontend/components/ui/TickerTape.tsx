"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { TrendingUp, TrendingDown } from "lucide-react";

const TICKERS = [
  "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
  "RELIANCE", "TCS", "INFY", "HDFCBANK", "WIPRO", "ICICIBANK",
  "JPM", "NFLX", "AMD",
];

interface Quote {
  ticker: string;
  price: number;
  pct_change: number;
  currency: string;
}

// Module-level cache — survives client-side navigation
let _cache: Quote[] | null = null;
let _inflight: Promise<Quote[]> | null = null;

async function getQuotes(): Promise<Quote[]> {
  if (_cache) return _cache;
  if (_inflight) return _inflight;

  _inflight = Promise.allSettled(
    TICKERS.map(async (ticker) => {
      const res = await fetch(`/api/stocks/${encodeURIComponent(ticker)}`);
      if (!res.ok) return null;
      const d = await res.json();
      if (d.price == null) return null;
      return {
        ticker: d.ticker ?? ticker,
        price: d.price as number,
        pct_change: (d.pct_change as number) ?? 0,
        currency: (d.currency as string) ?? "USD",
      };
    })
  ).then((results) => {
    const valid = results
      .filter((r): r is PromiseFulfilledResult<Quote | null> => r.status === "fulfilled")
      .map((r) => r.value)
      .filter((v): v is Quote => v !== null);
    _cache = valid;
    _inflight = null;
    return valid;
  });

  return _inflight;
}

function QuoteItem({ q, onClick }: { q: Quote; onClick: () => void }) {
  const up = q.pct_change >= 0;
  const color = up ? "text-emerald-500" : "text-rose-500";
  const sign = up ? "+" : "";
  const sym = q.currency === "INR" ? "₹" : "$";

  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-5 h-full hover:bg-muted/40 transition-colors flex-shrink-0 group"
    >
      <span className="text-xs font-mono font-bold text-foreground group-hover:text-primary transition-colors">
        {q.ticker}
      </span>
      <span className="text-xs text-muted-foreground">
        {sym}{q.price.toFixed(2)}
      </span>
      <span className={`flex items-center gap-0.5 text-[11px] font-semibold ${color}`}>
        {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
        {sign}{q.pct_change.toFixed(2)}%
      </span>
      <span className="text-border/50 ml-3 text-xs">|</span>
    </button>
  );
}

export function TickerTape() {
  const router = useRouter();
  const [quotes, setQuotes] = useState<Quote[]>(_cache ?? []);
  const [paused, setPaused] = useState(false);
  const trackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (_cache) { setQuotes(_cache); return; }
    getQuotes().then(setQuotes);
  }, []);

  // Set CSS variable for duration
  useEffect(() => {
    if (trackRef.current && quotes.length) {
      const duration = Math.max(quotes.length * 4, 40);
      trackRef.current.style.setProperty("--ticker-duration", `${duration}s`);
    }
  }, [quotes.length]);

  const sym = (q: Quote) => (q.currency === "INR" ? "₹" : "$");

  if (!quotes.length) {
    return (
      <div className="h-9 border-b border-border bg-muted/20 flex items-center gap-0 overflow-hidden">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 px-5 flex-shrink-0 animate-pulse">
            <div className="h-2 w-10 bg-muted rounded" />
            <div className="h-2 w-12 bg-muted/60 rounded" />
            <div className="h-2 w-10 bg-muted/40 rounded" />
          </div>
        ))}
      </div>
    );
  }

  // Duplicate for seamless loop
  const items = [...quotes, ...quotes];

  return (
    <div
      className="h-9 border-b border-border bg-background/95 backdrop-blur-sm overflow-hidden relative"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      {/* Fade edges */}
      <div className="absolute left-0 top-0 bottom-0 w-12 z-10 pointer-events-none bg-gradient-to-r from-background to-transparent" />
      <div className="absolute right-0 top-0 bottom-0 w-12 z-10 pointer-events-none bg-gradient-to-l from-background to-transparent" />

      <div
        ref={trackRef}
        className={`flex items-center h-full w-max ticker-scroll${paused ? " paused" : ""}`}
      >
        {items.map((q, i) => (
          <QuoteItem
            key={`${q.ticker}-${i}`}
            q={q}
            onClick={() => router.push(`/dashboard/${q.ticker}`)}
          />
        ))}
      </div>
    </div>
  );
}
