"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import type { FinancialsDetail } from "@/lib/api";

type StmtTab = "income" | "balance_sheet" | "cashflow";
type PeriodTab = "annual" | "quarterly";

interface Props {
  data: FinancialsDetail;
  ticker: string;
}

function fmt(val: unknown, currency: string, unit: string): string {
  const n = typeof val === "number" ? val : null;
  if (n == null || isNaN(n)) return "—";
  const sym = currency === "INR" ? "₹" : "$";
  const divisor = currency === "INR" ? 1e7 : 1e9;
  const display = n / divisor;
  if (Math.abs(display) >= 1000) return `${sym}${Math.round(display).toLocaleString()} ${unit}`;
  return `${sym}${display.toFixed(1)} ${unit}`;
}

function pct(val: unknown): string {
  const n = typeof val === "number" ? val : null;
  if (n == null || isNaN(n)) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function GrowthCell({ curr, prev }: { curr: unknown; prev: unknown }) {
  const c = typeof curr === "number" ? curr : null;
  const p = typeof prev === "number" ? prev : null;
  if (c == null || p == null || p === 0) return <td className="px-4 py-2.5 text-right text-xs text-muted-foreground">—</td>;
  const g = ((c - p) / Math.abs(p)) * 100;
  const color = g >= 0 ? "text-emerald-400" : "text-rose-400";
  return (
    <td className={`px-4 py-2.5 text-right text-xs font-medium ${color}`}>
      {g >= 0 ? "+" : ""}
      {g.toFixed(1)}%
    </td>
  );
}

interface RowDef {
  label: string;
  key: string;
  type?: "pct" | "value" | "ratio";
  indent?: boolean;
  bold?: boolean;
  separator?: boolean;
}

const INCOME_ROWS: RowDef[] = [
  { label: "Revenue", key: "revenue", bold: true },
  { label: "Gross Profit", key: "gross_profit", indent: true },
  { label: "Operating Income (EBIT)", key: "operating_income", indent: true },
  { label: "Total Operating Expenses", key: "total_expenses", indent: true },
  { label: "Net Profit", key: "net_income", bold: true },
  { label: "EBITDA", key: "ebitda" },
];

const BALANCE_ROWS: RowDef[] = [
  { label: "Total Assets", key: "total_assets", bold: true },
  { label: "Current Assets", key: "current_assets", indent: true },
  { label: "Total Liabilities", key: "total_liabilities", bold: true },
  { label: "Current Liabilities", key: "current_liabilities", indent: true },
  { label: "Long-term Debt", key: "long_term_debt", indent: true },
  { label: "Shareholder Equity", key: "total_equity", bold: true },
  { label: "Cash & Equivalents", key: "cash" },
];

const CASHFLOW_ROWS: RowDef[] = [
  { label: "Operating Cash Flow", key: "operating_cashflow", bold: true },
  { label: "Capital Expenditure", key: "capex", indent: true },
  { label: "Investing Cash Flow", key: "investing_cashflow" },
  { label: "Financing Cash Flow", key: "financing_cashflow" },
  { label: "Net Change in Cash", key: "net_change_in_cash", bold: true },
];

function DataTable({
  rows,
  periods,
  currency,
  unit,
  showGrowth,
}: {
  rows: RowDef[];
  periods: Record<string, unknown>[];
  currency: string;
  unit: string;
  showGrowth: boolean;
}) {
  if (!periods.length) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No data available
      </p>
    );
  }

  // newest first → reverse for column display (oldest left, newest right)
  const cols = [...periods].reverse();

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border">
            <th className="px-4 py-2.5 text-left font-semibold text-muted-foreground w-48">
              Particulars
            </th>
            {cols.map((p) => (
              <th
                key={String(p.period)}
                className="px-4 py-2.5 text-right font-semibold text-foreground"
              >
                {String(p.period || "")}
              </th>
            ))}
            {showGrowth && cols.length >= 2 && (
              <th className="px-4 py-2.5 text-right font-semibold text-muted-foreground">
                YoY
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.key}
              className="border-b border-border/50 hover:bg-muted/20 transition-colors"
            >
              <td
                className={`px-4 py-2.5 ${row.indent ? "pl-8" : ""} ${
                  row.bold ? "font-semibold text-foreground" : "text-muted-foreground"
                }`}
              >
                {row.label}
              </td>
              {cols.map((p) => (
                <td key={String(p.period)} className="px-4 py-2.5 text-right text-foreground">
                  {fmt(p[row.key], currency, unit)}
                </td>
              ))}
              {showGrowth && cols.length >= 2 && (
                <GrowthCell
                  curr={cols[cols.length - 1][row.key]}
                  prev={cols[cols.length - 2][row.key]}
                />
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function FinancialsDetailView({ data, ticker }: Props) {
  const [stmtTab, setStmtTab] = useState<StmtTab>("income");
  const [periodTab, setPeriodTab] = useState<PeriodTab>("annual");

  const isIncome = stmtTab === "income";
  const canToggle = isIncome;

  const rows =
    stmtTab === "income"
      ? INCOME_ROWS
      : stmtTab === "balance_sheet"
      ? BALANCE_ROWS
      : CASHFLOW_ROWS;

  const periods =
    stmtTab === "income"
      ? periodTab === "annual"
        ? data.income_annual
        : data.income_quarterly
      : stmtTab === "balance_sheet"
      ? data.balance_sheet
      : data.cashflow;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {/* Back nav */}
        <Link
          href={`/dashboard/${ticker}`}
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to {ticker}
        </Link>

        {/* Title */}
        <div>
          <h1 className="text-xl font-bold text-foreground">{ticker} — Financials</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            All values in {data.currency} {data.currency_unit}
          </p>
        </div>

        {/* Statement type tabs */}
        <div className="flex gap-1 border-b border-border">
          {(["income", "balance_sheet", "cashflow"] as StmtTab[]).map((t) => (
            <button
              key={t}
              onClick={() => {
                setStmtTab(t);
                if (t !== "income") setPeriodTab("annual");
              }}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
                stmtTab === t
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {t === "income"
                ? "Income Statement"
                : t === "balance_sheet"
                ? "Balance Sheet"
                : "Cash Flow"}
            </button>
          ))}
        </div>

        {/* Period toggle (only for income) */}
        <div className="flex items-center justify-between">
          <div className="flex rounded-lg bg-muted p-0.5 text-xs w-fit">
            {(["annual", "quarterly"] as PeriodTab[]).map((t) => (
              <button
                key={t}
                onClick={() => canToggle && setPeriodTab(t)}
                disabled={!canToggle}
                className={`px-3 py-1.5 rounded-md transition-colors ${
                  periodTab === t
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground"
                } ${!canToggle ? "opacity-40 cursor-not-allowed" : "hover:text-foreground"}`}
              >
                {t === "annual" ? "Yearly" : "Quarterly"}
              </button>
            ))}
          </div>
          {!canToggle && (
            <p className="text-[11px] text-muted-foreground">
              Quarterly data not available for {stmtTab === "balance_sheet" ? "Balance Sheet" : "Cash Flow"}
            </p>
          )}
        </div>

        {/* Data table */}
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <DataTable
            rows={rows}
            periods={periods as Record<string, unknown>[]}
            currency={data.currency}
            unit={data.currency_unit}
            showGrowth={periodTab === "annual"}
          />
        </div>
      </div>
    </div>
  );
}
