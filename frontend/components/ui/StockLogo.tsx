"use client";

import { useState } from "react";

interface Props {
  website?: string | null;
  ticker: string;
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

type Source = "fmp" | "clearbit" | "google" | "fallback";

export function StockLogo({ website, ticker, size = 48, className = "" }: Props) {
  const [source, setSource] = useState<Source>("fmp");

  const domain = domainFromUrl(website);
  const clean = cleanTicker(ticker);
  const initials = clean.slice(0, 2).toUpperCase();
  const fontSize = size <= 24 ? "text-[9px]" : size <= 36 ? "text-xs" : "text-sm";
  const style = { width: size, height: size, minWidth: size };

  const nextSource = (): Source => {
    if (source === "fmp") return domain ? "clearbit" : "google";
    if (source === "clearbit") return domain ? "google" : "fallback";
    if (source === "google") return "fallback";
    return "fallback";
  };

  const src: string | null =
    source === "fmp"
      ? `https://financialmodelingprep.com/image-stock/${clean}.png`
      : source === "clearbit" && domain
      ? `https://logo.clearbit.com/${domain}`
      : source === "google" && domain
      ? `https://www.google.com/s2/favicons?domain=${domain}&sz=64`
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
