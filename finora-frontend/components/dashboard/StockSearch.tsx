"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StockSearchResult } from "@/lib/api";

interface Props {
  compact?: boolean;
}

export function StockSearch({ compact = false }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const search = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); return; }
    setLoading(true);
    try {
      const res = await fetch(`/api/stocks/search?q=${encodeURIComponent(q)}&limit=8`);
      const data: StockSearchResult[] = await res.json();
      setResults(data);
      setSelected(0);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(query), 150);
    return () => clearTimeout(debounceRef.current);
  }, [query, search]);

  const navigate = (ticker: string) => {
    setOpen(false);
    setQuery("");
    setResults([]);
    router.push(`/dashboard/${encodeURIComponent(ticker)}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setSelected(s => Math.min(s + 1, results.length - 1)); }
    if (e.key === "ArrowUp") { e.preventDefault(); setSelected(s => Math.max(s - 1, 0)); }
    if (e.key === "Enter" && results[selected]) navigate(results[selected].ticker);
  };

  const modal = open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]" onClick={() => setOpen(false)}>
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
          <div
            className="relative w-full max-w-lg bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
              <Search className="w-4 h-4 text-muted-foreground flex-shrink-0" />
              <input
                ref={inputRef}
                className="flex-1 bg-transparent text-foreground placeholder:text-muted-foreground outline-none text-sm"
                placeholder="Search stocks by ticker or name..."
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                autoComplete="off"
              />
              {loading && <div className="w-3 h-3 border border-primary border-t-transparent rounded-full animate-spin" />}
            </div>

            {results.length > 0 && (
              <ul className="max-h-80 overflow-y-auto py-2">
                {results.map((s, i) => (
                  <li key={s.ticker}>
                    <button
                      className={cn(
                        "w-full flex items-center gap-3 px-4 py-2.5 hover:bg-accent transition-colors text-left",
                        i === selected && "bg-accent"
                      )}
                      onClick={() => navigate(s.ticker)}
                      onMouseEnter={() => setSelected(i)}
                    >
                      <div className="w-8 h-8 rounded-md bg-secondary flex items-center justify-center flex-shrink-0">
                        <TrendingUp className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-semibold text-foreground text-sm">{s.ticker}</span>
                          <span className="text-xs text-muted-foreground">{s.exchange}</span>
                          {s.country === "IN" && <span className="text-xs bg-orange-500/15 text-orange-400 px-1.5 py-0.5 rounded font-medium">NSE</span>}
                        </div>
                        <div className="text-xs text-muted-foreground truncate">{s.name}</div>
                      </div>
                      {s.sector && <span className="text-xs text-muted-foreground hidden sm:block">{s.sector}</span>}
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {query && !loading && results.length === 0 && (
              <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                No stocks found for &quot;{query}&quot;
              </div>
            )}

            {!query && (
              <div className="px-4 py-3 text-xs text-muted-foreground border-t border-border flex items-center justify-between">
                <span>↑↓ navigate · Enter select · Esc close</span>
                <span>US · India · Global · 555 stocks</span>
              </div>
            )}
          </div>
        </div>
  );

  if (compact) {
    return (
      <>
        <button
          onClick={() => { setOpen(true); setTimeout(() => inputRef.current?.focus(), 50); }}
          className="flex items-center gap-2 px-2.5 sm:px-3 py-1.5 rounded-md bg-secondary hover:bg-accent transition-colors text-xs sm:text-sm text-muted-foreground border border-border"
        >
          <Search className="w-3.5 h-3.5 flex-shrink-0" />
          <span className="hidden xs:inline sm:inline">Search stocks</span>
        </button>
        {modal}
      </>
    );
  }

  return (
    <>
      <button
        onClick={() => { setOpen(true); setTimeout(() => inputRef.current?.focus(), 50); }}
        className="w-full max-w-md flex items-center gap-3 px-4 py-3 rounded-xl bg-secondary border border-border hover:border-primary/40 transition-colors text-left"
      >
        <Search className="w-4 h-4 text-muted-foreground flex-shrink-0" />
        <span className="text-muted-foreground text-sm flex-1">Search 555 stocks — AAPL, RELIANCE, INFY...</span>
      </button>

      {modal}
    </>
  );
}
