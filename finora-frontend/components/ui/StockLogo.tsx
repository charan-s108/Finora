"use client";

import { useState } from "react";

interface Props {
  website?: string | null;
  ticker: string;
  exchange?: string | null;
  size?: number;
  className?: string;
}

function domainFromUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const { hostname } = new URL(url.startsWith("http") ? url : `https://${url}`);
    return hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

function cleanTicker(ticker: string): string {
  return ticker.replace(/\.(NS|BO|L|TO|AX|HK|SS|SZ)$/i, "");
}

function tickerColor(ticker: string): string {
  const colors = [
    "bg-violet-500", "bg-indigo-500", "bg-blue-500", "bg-cyan-500",
    "bg-emerald-500", "bg-teal-500", "bg-orange-500", "bg-rose-500",
    "bg-pink-500", "bg-purple-500",
  ];
  const idx = ticker.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) % colors.length;
  return colors[idx];
}

// Source priority chain:
// US stocks:     fmp → clearbit (domain) → tv → google (domain) → fallback
// Indian stocks: tv  → clearbit (domain) → google (domain)      → fallback
type Source = "fmp" | "tv" | "clearbit" | "google" | "fallback";

const FMP_UNSUPPORTED = new Set(["NSE", "BSE"]);

function initialSource(domain: string | null, exchange: string | null | undefined): Source {
  if (exchange && FMP_UNSUPPORTED.has(exchange.toUpperCase())) return "tv";
  if (domain?.endsWith(".in")) return "tv";
  return "fmp";
}

export function StockLogo({ website, ticker, exchange, size = 48, className = "" }: Props) {
  const domain = domainFromUrl(website);
  const [source, setSource] = useState<Source>(() => initialSource(domain, exchange));

  const clean = cleanTicker(ticker);
  const initials = clean.slice(0, 2).toUpperCase();
  const fontSize = size <= 24 ? "text-[9px]" : size <= 36 ? "text-xs" : "text-sm";
  const style = { width: size, height: size, minWidth: size };

  const nextSource = (): Source => {
    if (source === "fmp") return domain ? "clearbit" : "tv";
    if (source === "tv") return domain ? "clearbit" : "fallback";
    if (source === "clearbit") return domain ? "google" : "fallback";
    if (source === "google") return "fallback";
    return "fallback";
  };

  const src: string | null =
    source === "fmp"
      ? `https://financialmodelingprep.com/image-stock/${clean}.png`
      : source === "tv"
      ? `https://s3-symbol-logo.tradingview.com/${clean.toLowerCase()}--big.svg`
      : source === "clearbit" && domain
      ? `https://logo.clearbit.com/${domain}`
      : source === "google" && domain
      ? `https://t2.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://${domain}&size=64`
      : null;

  if (source === "fallback" || !src) {
    return (
      <div
        style={style}
        className={`rounded-xl ${tickerColor(ticker)} flex items-center justify-center flex-shrink-0 ${className}`}
      >
        <span className={`font-mono font-bold text-white ${fontSize}`}>{initials}</span>
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={ticker}
      width={size}
      height={size}
      style={style}
      className={`rounded-xl object-contain bg-white p-1 flex-shrink-0 ${className}`}
      onError={() => setSource(nextSource())}
    />
  );
}
