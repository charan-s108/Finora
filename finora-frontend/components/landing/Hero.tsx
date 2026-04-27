"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, TrendingUp, Flame, Users, Zap, Globe } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StockSearchResult } from "@/lib/api";

function GitHubBadge() {
  return (
    <a
      href="https://github.com/charan-s108/Finora"
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-primary/30 bg-primary/5 hover:bg-primary/10 transition-colors text-sm font-medium text-primary mb-8 group"
    >
      <Flame className="w-4 h-4 text-orange-500" />
      <span>Open Source on GitHub</span>
      <span className="text-xs text-muted-foreground group-hover:text-foreground transition-colors">
        View repo →
      </span>
    </a>
  );
}

function SocialProof() {
  const avatarColors = [
    "bg-purple-500",
    "bg-indigo-500",
    "bg-violet-500",
    "bg-fuchsia-500",
    "bg-pink-500",
  ];
  return (
    <div className="flex items-center gap-3 mt-8">
      <div className="flex -space-x-2">
        {avatarColors.map((color, i) => (
          <div
            key={i}
            className={`w-8 h-8 rounded-full ${color} border-2 border-background flex items-center justify-center`}
          >
            <Users className="w-3.5 h-3.5 text-white" />
          </div>
        ))}
      </div>
      <div className="text-sm">
        <span className="font-semibold text-foreground">Built for NRI</span>
        <span className="text-muted-foreground"> &amp; global investors</span>
      </div>
      <div className="flex items-center gap-1 text-emerald-500 text-xs font-medium ml-1">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        Live
      </div>
    </div>
  );
}

function StockSearchHero() {
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
      setResults(await res.json());
      setSelected(0);
    } catch { setResults([]); }
    finally { setLoading(false); }
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

  return (
    <>
      {/* Search trigger */}
      <button
        onClick={() => { setOpen(true); setTimeout(() => inputRef.current?.focus(), 60); }}
        className="group relative w-full max-w-xl flex items-center gap-3 px-5 py-4 rounded-2xl bg-card border border-border hover:border-primary/50 shadow-lg hover:shadow-primary/10 transition-all text-left"
      >
        <Search className="w-5 h-5 text-muted-foreground flex-shrink-0 group-hover:text-primary transition-colors" />
        <span className="text-muted-foreground flex-1">
          Search 555+ stocks — AAPL, RELIANCE, INFY...
        </span>
      </button>

      {/* Quick suggestions */}
      <div className="flex flex-wrap items-center gap-2 mt-3 justify-center">
        {["AAPL", "NVDA", "RELIANCE", "TCS", "MSFT", "INFY"].map((t) => (
          <button
            key={t}
            onClick={() => navigate(t)}
            className="px-3 py-1 rounded-full text-xs font-mono font-semibold border border-border bg-card hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all"
          >
            {t}
          </button>
        ))}
      </div>

      {/* Search modal */}
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh] px-4"
          onClick={() => setOpen(false)}
        >
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
          <div
            className="relative w-full max-w-xl bg-card border border-border rounded-2xl shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 px-5 py-4 border-b border-border">
              <Search className="w-4 h-4 text-muted-foreground flex-shrink-0" />
              <input
                ref={inputRef}
                className="flex-1 bg-transparent text-foreground placeholder:text-muted-foreground outline-none text-sm"
                placeholder="Search stocks by ticker or name..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                autoComplete="off"
              />
              {loading && (
                <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              )}
              <kbd className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded border border-border font-mono">
                Esc
              </kbd>
            </div>

            {results.length > 0 && (
              <ul className="max-h-80 overflow-y-auto py-2">
                {results.map((s, i) => (
                  <li key={s.ticker}>
                    <button
                      className={cn(
                        "w-full flex items-center gap-3 px-5 py-3 hover:bg-accent transition-colors text-left",
                        i === selected && "bg-accent"
                      )}
                      onClick={() => navigate(s.ticker)}
                      onMouseEnter={() => setSelected(i)}
                    >
                      <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <TrendingUp className="w-4 h-4 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-foreground">{s.ticker}</span>
                          <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                            {s.exchange}
                          </span>
                          {s.country === "IN" && (
                            <span className="text-xs bg-orange-500/15 text-orange-500 px-1.5 py-0.5 rounded font-medium">
                              India
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-muted-foreground truncate">{s.name}</div>
                      </div>
                      {s.sector && (
                        <span className="text-xs text-muted-foreground hidden sm:block">{s.sector}</span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {query && !loading && results.length === 0 && (
              <div className="px-5 py-10 text-center text-muted-foreground">
                No stocks found for &quot;{query}&quot;
              </div>
            )}

            {!query && (
              <div className="px-5 py-3 text-xs text-muted-foreground border-t border-border flex items-center justify-between">
                <span>↑↓ navigate · Enter select · Esc close</span>
                <span>US · India · Global · 555 stocks</span>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export function Hero() {
  return (
    <section className="relative flex flex-col items-center justify-center min-h-[calc(100svh-110px)] px-4 py-16 text-center overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 gradient-hero-light dark:gradient-hero-dark pointer-events-none" />

      {/* Decorative blobs */}
      <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-primary/8 dark:bg-primary/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center max-w-4xl mx-auto">
        <GitHubBadge />

        <h1 className="font-heading font-bold text-4xl sm:text-5xl md:text-6xl lg:text-7xl leading-tight tracking-tight text-foreground mb-5">
          AI Financial Intelligence{" "}
          <span className="text-gradient">for Global Investors</span>
        </h1>

        <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl leading-relaxed mb-10">
          Real-time analysis for 555+ US &amp; Indian stocks — powered by multi-layer RAG, 20-year
          historical patterns, and Groq AI. Built for NRI investors.
        </p>

        {/* Badges */}
        <div className="flex flex-wrap items-center justify-center gap-3 mb-10">
          {[
            { icon: <Zap className="w-3.5 h-3.5" />, label: "Real-time Data" },
            { icon: <Globe className="w-3.5 h-3.5" />, label: "US · India · Global" },
            { icon: <TrendingUp className="w-3.5 h-3.5" />, label: "20-Year Patterns" },
          ].map(({ icon, label }) => (
            <span
              key={label}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary/8 dark:bg-primary/15 text-primary text-xs font-semibold border border-primary/20"
            >
              {icon}
              {label}
            </span>
          ))}
        </div>

        {/* Search */}
        <div className="w-full flex flex-col items-center">
          <StockSearchHero />
        </div>

        <SocialProof />
      </div>
    </section>
  );
}
