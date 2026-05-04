"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { StockDetail } from "@/lib/api";
import { formatCurrency, formatPct } from "@/lib/format";
import { Sparkline } from "@/components/ui/sparkline";
import { StockLogo } from "@/components/ui/StockLogo";

interface Props {
  stock: StockDetail;
}

export function StockHeader({ stock }: Props) {
  const positive = (stock.pct_change ?? 0) >= 0;
  const neutral = stock.pct_change == null;
  const sparkData = (stock.ohlcv_7d ?? []).map((d) => d.close);

  return (
    <div className="card-dark p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
      <div className="flex items-start gap-3 sm:gap-4">
        <StockLogo website={stock.website} ticker={stock.ticker} exchange={stock.exchange} size={40} className="sm:[&>img]:size-12" />
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-lg sm:text-2xl font-bold font-mono text-foreground">
              {stock.ticker}
            </h1>
            {stock.sector && (
              <span className="text-[10px] sm:text-xs bg-secondary px-2 py-0.5 rounded text-muted-foreground border border-border">
                {stock.sector}
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
            {stock.name ?? stock.ticker}
          </p>
        </div>
      </div>

      <div className="flex items-end gap-3 sm:gap-6">
        {sparkData.length > 1 && (
          <Sparkline
            data={sparkData}
            positive={positive}
            className="hidden sm:block"
          />
        )}

        <div className="text-right">
          <div className="text-2xl sm:text-3xl font-bold font-mono text-foreground leading-none">
            {stock.price != null
              ? formatCurrency(stock.price, stock.currency === "INR" ? "INR" : "USD")
              : "—"}
          </div>

          <div
            className={`flex items-center justify-end gap-1 mt-1 ${
              neutral
                ? "text-muted-foreground"
                : positive
                  ? "text-positive"
                  : "text-negative"
            }`}
          >
            {!neutral &&
              (positive ? (
                <TrendingUp className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              ) : (
                <TrendingDown className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              ))}
            {neutral && <Minus className="w-3.5 h-3.5 sm:w-4 sm:h-4" />}
            <span className="text-xs sm:text-sm font-semibold font-mono">
              {stock.change != null
                ? formatCurrency(
                    stock.change,
                    stock.currency === "INR" ? "INR" : "USD"
                  )
                : "—"}
            </span>
            <span className="text-xs sm:text-sm font-semibold font-mono">
              ({formatPct(stock.pct_change)})
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}