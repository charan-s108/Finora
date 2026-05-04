"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import { Building2, Globe, Users, MapPin, TrendingUp, Percent, ExternalLink, ChevronDown, ChevronUp } from "lucide-react";
import type { StockDetail } from "@/lib/api";

interface Props {
  stock: StockDetail;
}

function formatEmployees(n?: number | null) {
  if (!n) return null;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return n.toLocaleString();
}

function StatRow({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2.5 py-2 border-b border-border last:border-0">
      <span className="text-muted-foreground/60 flex-shrink-0">{icon}</span>
      <span className="text-xs text-muted-foreground w-24 flex-shrink-0">{label}</span>
      <span className="text-xs font-medium text-foreground text-right ml-auto">{value}</span>
    </div>
  );
}

export function StockAbout({ stock }: Props) {
  const [expanded, setExpanded] = useState(false);
  const employees = formatEmployees(stock.full_time_employees);
  const location = [stock.city, stock.country].filter(Boolean).join(", ");
  const hasStats = stock.beta != null || stock.dividend_yield != null || employees || location || stock.industry;
  const summaryLong = (stock.business_summary?.length ?? 0) > 300;

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center gap-2">
        <Building2 className="w-4 h-4 text-primary" />
        <h3 className="text-sm font-semibold text-foreground">About</h3>
        <span className="text-xs text-muted-foreground ml-1">{stock.name || stock.ticker}</span>
      </div>

      <div className="p-4 space-y-4">
        {/* Business summary */}
        {stock.business_summary ? (
          <div>
            <p className={`text-xs text-muted-foreground leading-relaxed ${expanded ? "" : "line-clamp-4"}`}>
              {stock.business_summary}
            </p>
            {summaryLong && (
              <button
                onClick={() => setExpanded((v) => !v)}
                className="mt-1.5 inline-flex items-center gap-1 text-[11px] text-primary hover:underline font-medium"
              >
                {expanded ? (
                  <><ChevronUp className="w-3 h-3" /> Show less</>
                ) : (
                  <><ChevronDown className="w-3 h-3" /> Show more</>
                )}
              </button>
            )}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground italic">
            No business description available.
          </p>
        )}

        {/* Stats */}
        {hasStats && (
          <div className="rounded-lg border border-border bg-muted/20 px-3 py-1">
            {stock.industry && (
              <StatRow
                icon={<Building2 className="w-3 h-3" />}
                label="Industry"
                value={stock.industry}
              />
            )}
            {location && (
              <StatRow
                icon={<MapPin className="w-3 h-3" />}
                label="Headquarters"
                value={location}
              />
            )}
            {employees && (
              <StatRow
                icon={<Users className="w-3 h-3" />}
                label="Employees"
                value={employees}
              />
            )}
            {stock.beta != null && (
              <StatRow
                icon={<TrendingUp className="w-3 h-3" />}
                label="Beta"
                value={stock.beta.toFixed(2)}
              />
            )}
            {stock.dividend_yield != null && stock.dividend_yield > 0 && (
              <StatRow
                icon={<Percent className="w-3 h-3" />}
                label="Dividend Yield"
                value={`${(stock.dividend_yield * 100).toFixed(2)}%`}
              />
            )}
          </div>
        )}

        {/* Website link */}
        {stock.website && (
          <a
            href={stock.website}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline font-medium"
          >
            <Globe className="w-3 h-3" />
            {stock.website.replace(/^https?:\/\/(www\.)?/, "")}
            <ExternalLink className="w-2.5 h-2.5" />
          </a>
        )}
      </div>
    </div>
  );
}
