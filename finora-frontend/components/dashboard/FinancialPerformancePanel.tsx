"use client";

import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { FinancialPerformance, FinancialPeriod } from "@/lib/api";
import { FinancialsModal } from "@/components/dashboard/FinancialsModal";

type Tab = "annual" | "quarterly";

interface Props {
  data: FinancialPerformance;
  ticker: string;
}

function GrowthBadge({ pct }: { pct?: number | null }) {
  if (pct == null) return null;
  const positive = pct >= 0;
  return (
    <span
      className={`text-[11px] font-semibold px-1.5 py-0.5 rounded-full ${
        positive
          ? "bg-emerald-500/15 text-emerald-400"
          : "bg-rose-500/15 text-rose-400"
      }`}
    >
      {positive ? "+" : ""}
      {pct.toFixed(1)}%
    </span>
  );
}

function GrowthRow({
  label,
  g1y,
  cagr,
}: {
  label: string;
  g1y?: number | null;
  cagr?: number | null;
}) {
  return (
    <div className="space-y-1 text-center">
      <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">
        {label}
      </p>
      <div className="flex items-center justify-center gap-2">
        {g1y != null && (
          <div className="text-center">
            <p className="text-[9px] text-muted-foreground">1Y (TTM)</p>
            <GrowthBadge pct={g1y} />
          </div>
        )}
        {cagr != null && (
          <div className="text-center">
            <p className="text-[9px] text-muted-foreground">3Y CAGR</p>
            <GrowthBadge pct={cagr} />
          </div>
        )}
        {g1y == null && cagr == null && (
          <span className="text-[11px] text-muted-foreground">—</span>
        )}
      </div>
    </div>
  );
}

function ChartTick({ x, y, payload }: { x?: number; y?: number; payload?: { value: string } }) {
  return (
    <text
      x={x}
      y={y}
      dy={12}
      textAnchor="middle"
      fontSize={10}
      fill="currentColor"
      style={{ color: "var(--muted-foreground)" }}
    >
      {payload?.value}
    </text>
  );
}

function formatValue(val: number | null | undefined, sym: string, unit: string): string {
  if (val == null) return "—";
  return `${sym}${val.toLocaleString()} ${unit}`;
}

interface ChartPayloadEntry {
  name: string;
  value: number;
  color: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: ChartPayloadEntry[];
  label?: string;
  sym: string;
  unit: string;
}

function CustomTooltip({ active, payload, label, sym, unit }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-card/95 backdrop-blur-sm p-2.5 text-xs shadow-lg">
      <p className="font-semibold text-foreground mb-1">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color }}>
          {entry.name}: {sym}
          {entry.value != null ? entry.value.toLocaleString() : "—"} {unit}
        </p>
      ))}
    </div>
  );
}

export function FinancialPerformancePanel({ data, ticker }: Props) {
  const [tab, setTab] = useState<Tab>("annual");
  const [showModal, setShowModal] = useState(false);

  const periods: FinancialPeriod[] = tab === "annual" ? data.annual : data.quarterly;
  const chartData = [...periods].reverse(); // oldest → newest left → right
  const latest = periods[0];
  const sym = data.currency === "INR" ? "₹" : "$";
  const unit = data.currency_unit;

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/20">
        <h3 className="text-sm font-semibold text-foreground">Financial Performance</h3>
        <div className="flex items-center gap-3">
          {/* Q/Y toggle */}
          <div className="flex rounded-lg bg-muted p-0.5 text-xs">
            {(["quarterly", "annual"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-2.5 py-1 rounded-md transition-colors ${
                  tab === t
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {t === "quarterly" ? "Quarterly" : "Yearly"}
              </button>
            ))}
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="text-[11px] text-primary hover:underline whitespace-nowrap"
          >
            All Financials →
          </button>
        </div>
      </div>

      <div className="px-4 py-3 space-y-3">
        {/* Latest period summary */}
        {latest && (
          <div className="flex gap-6">
            <div className="space-y-1">
              <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">
                Revenue ({unit})
              </p>
              <p className="text-base font-bold text-foreground">
                {formatValue(latest.revenue, sym, unit)}
              </p>
              <GrowthBadge pct={latest.revenue_growth_pct} />
            </div>
            <div className="space-y-1">
              <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">
                Net Profit ({unit})
              </p>
              <p className="text-base font-bold text-foreground">
                {formatValue(latest.net_income, sym, unit)}
              </p>
              <GrowthBadge pct={latest.profit_growth_pct} />
            </div>
          </div>
        )}

        {/* Bar chart */}
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={chartData} barGap={2} barCategoryGap="25%">
              <XAxis
                dataKey="period"
                tick={<ChartTick />}
                axisLine={false}
                tickLine={false}
              />
              <YAxis hide />
              <Tooltip
                content={<CustomTooltip sym={sym} unit={unit} />}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              <Legend
                iconType="circle"
                iconSize={6}
                wrapperStyle={{ fontSize: 10, paddingTop: 4, color: "var(--foreground)" }}
              />
              <Bar
                dataKey="revenue"
                name="Revenue"
                fill="#6B7280"
                radius={[2, 2, 0, 0]}
              />
              <Bar
                dataKey="net_income"
                name="Net Profit"
                fill="#10B981"
                radius={[2, 2, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-xs text-muted-foreground py-6 text-center">
            No financial data available
          </p>
        )}

        {/* Growth summary */}
        <div className="grid grid-cols-2 gap-3 border-t border-border pt-3">
          <GrowthRow
            label="Revenue Growth"
            g1y={data.revenue_1y_growth}
            cagr={data.revenue_3y_cagr}
          />
          <GrowthRow
            label="Profit Growth"
            g1y={data.profit_1y_growth}
            cagr={data.profit_3y_cagr}
          />
        </div>
      </div>

      <FinancialsModal
        ticker={ticker}
        isOpen={showModal}
        onClose={() => setShowModal(false)}
      />
    </div>
  );
}
