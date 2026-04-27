import type { StockSearchResult } from "./api";

let _cache: StockSearchResult[] | null = null;

export async function loadUniverse(): Promise<StockSearchResult[]> {
  if (_cache) return _cache;
  try {
    const res = await fetch("/api/stocks/search?q=&limit=600");
    if (!res.ok) return [];
    _cache = await res.json();
    return _cache ?? [];
  } catch {
    return [];
  }
}

export function searchUniverse(stocks: StockSearchResult[], query: string, limit = 10): StockSearchResult[] {
  if (!query.trim()) return stocks.slice(0, limit);
  const q = query.toLowerCase();
  const scored = stocks
    .map((s) => {
      const ticker = s.ticker.toLowerCase();
      const name = (s.name || "").toLowerCase();
      let score = 0;
      if (ticker === q) score = 200;
      else if (ticker.startsWith(q)) score = 170 + (10 - ticker.length);
      else if (name.startsWith(q)) score = 100;
      else if (ticker.includes(q)) score = 80;
      else if (name.includes(q)) score = 60;
      return { stock: s, score };
    })
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score);
  return scored.slice(0, limit).map((x) => x.stock);
}
