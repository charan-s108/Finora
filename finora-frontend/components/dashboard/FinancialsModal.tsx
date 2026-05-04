"use client";

import { useState, useEffect, useCallback } from "react";
import { X, Loader2 } from "lucide-react";
import { getFinancials, type FinancialsDetail } from "@/lib/api";

type StmtTab = "income" | "balance_sheet" | "cashflow";
type PeriodTab = "annual" | "quarterly";

interface Props {
  ticker: string;
  isOpen: boolean;
  onClose: () => void;
}

interface RowDef {
  label: string;
  key: string;
  indent?: boolean;
  bold?: boolean;
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

function fmtVal(val: unknown, currency: string, unit: string): string {
  const n = typeof val === "number" ? val : null;
  if (n == null || isNaN(n)) return "—";
  const sym = currency === "INR" ? "₹" : "$";
  const divisor = currency === "INR" ? 1e7 : 1e9;
  const display = n / divisor;
  if (Math.abs(display) >= 1000) return `${sym}${Math.round(display).toLocaleString()} ${unit}`;
  return `${sym}${display.toFixed(1)} ${unit}`;
}

function GrowthCell({ curr, prev }: { curr: unknown; prev: unknown }) {
  const c = typeof curr === "number" ? curr : null;
  const p = typeof prev === "number" ? prev : null;
  if (c == null || p == null || p === 0)
    return <td className="px-3 py-2 text-right text-xs text-muted-foreground">—</td>;
  const g = ((c - p) / Math.abs(p)) * 100;
  return (
    <td
      className={`px-3 py-2 text-right text-xs font-semibold ${
        g >= 0 ? "text-emerald-400" : "text-rose-400"
      }`}
    >
      {g >= 0 ? "+" : ""}
      {g.toFixed(1)}%
    </td>
  );
}

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
  if (!periods.length)
    return (
      <div className="py-12 text-center space-y-1">
        <p className="text-sm text-muted-foreground">No data available</p>
        <p className="text-xs text-muted-foreground/60">
          This data may not be available for this stock via Yahoo Finance
        </p>
      </div>
    );

  const cols = [...periods].reverse();

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs min-w-[600px]">
        <thead>
          <tr className="border-b border-border">
            <th className="px-3 py-2.5 text-left font-semibold text-muted-foreground w-44 sticky left-0 bg-card">
              Particulars
            </th>
            {cols.map((p) => (
              <th key={String(p.period)} className="px-3 py-2.5 text-right font-semibold text-foreground whitespace-nowrap">
                {String(p.period || "")}
              </th>
            ))}
            {showGrowth && cols.length >= 2 && (
              <th className="px-3 py-2.5 text-right font-semibold text-muted-foreground whitespace-nowrap">
                YoY
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="border-b border-border/40 hover:bg-muted/20 transition-colors">
              <td
                className={`px-3 py-2 sticky left-0 bg-card ${row.indent ? "pl-7" : ""} ${
                  row.bold ? "font-semibold text-foreground" : "text-muted-foreground"
                }`}
              >
                {row.label}
              </td>
              {cols.map((p) => (
                <td key={String(p.period)} className="px-3 py-2 text-right text-foreground whitespace-nowrap">
                  {fmtVal(p[row.key], currency, unit)}
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

function ModalContent({ data, ticker }: { data: FinancialsDetail; ticker: string }) {
  const [stmtTab, setStmtTab] = useState<StmtTab>("income");
  const [periodTab, setPeriodTab] = useState<PeriodTab>("annual");
  const isIncome = stmtTab === "income";

  const rows = stmtTab === "income" ? INCOME_ROWS : stmtTab === "balance_sheet" ? BALANCE_ROWS : CASHFLOW_ROWS;
  const periods =
    stmtTab === "income"
      ? periodTab === "annual"
        ? data.income_annual
        : data.income_quarterly
      : stmtTab === "balance_sheet"
      ? data.balance_sheet
      : data.cashflow;

  return (
    <div className="flex flex-col h-full">
      {/* Statement tabs */}
      <div className="flex gap-1 border-b border-border px-4 flex-shrink-0">
        {(["income", "balance_sheet", "cashflow"] as StmtTab[]).map((t) => (
          <button
            key={t}
            onClick={() => {
              setStmtTab(t);
              if (t !== "income") setPeriodTab("annual");
            }}
            className={`px-3 py-2.5 text-xs font-medium border-b-2 transition-colors -mb-px whitespace-nowrap ${
              stmtTab === t
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t === "income" ? "Income Statement" : t === "balance_sheet" ? "Balance Sheet" : "Cash Flow"}
          </button>
        ))}
      </div>

      {/* Period toggle */}
      <div className="flex items-center gap-3 px-4 py-2.5 border-b border-border/50 flex-shrink-0">
        <div className="flex rounded-lg bg-muted p-0.5 text-xs w-fit">
          {(["annual", "quarterly"] as PeriodTab[]).map((t) => (
            <button
              key={t}
              onClick={() => isIncome && setPeriodTab(t)}
              disabled={!isIncome}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                periodTab === t ? "bg-background text-foreground shadow-sm" : "text-muted-foreground"
              } ${!isIncome ? "opacity-40 cursor-not-allowed" : "hover:text-foreground"}`}
            >
              {t === "annual" ? "Yearly" : "Quarterly"}
            </button>
          ))}
        </div>
        <span className="text-[10px] text-muted-foreground">
          All values in {data.currency} {data.currency_unit}
        </span>
      </div>

      {/* Table */}
      <div className="overflow-auto flex-1">
        <DataTable
          rows={rows}
          periods={periods as Record<string, unknown>[]}
          currency={data.currency}
          unit={data.currency_unit}
          showGrowth={periodTab === "annual"}
        />
      </div>
    </div>
  );
}

export function FinancialsModal({ ticker, isOpen, onClose }: Props) {
  const [data, setData] = useState<FinancialsDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const result = await getFinancials(ticker);
      if (result) setData(result);
      else setError(true);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [ticker]);

  useEffect(() => {
    if (isOpen && !data) fetchData();
  }, [isOpen, data, fetchData]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-card border border-border rounded-xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border flex-shrink-0">
          <div>
            <h2 className="text-sm font-semibold text-foreground">{ticker} — Financial Statements</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 min-h-0 overflow-hidden">
          {loading && (
            <div className="flex items-center justify-center py-16 gap-2 text-muted-foreground">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">Loading financial data…</span>
            </div>
          )}
          {error && !loading && (
            <div className="py-16 text-center space-y-1">
              <p className="text-sm text-muted-foreground">Failed to load financial data</p>
              <button
                onClick={() => fetchData()}
                className="text-xs text-primary hover:underline mt-2"
              >
                Retry
              </button>
            </div>
          )}
          {data && !loading && <ModalContent data={data} ticker={ticker} />}
        </div>
      </div>
    </div>
  );
}
