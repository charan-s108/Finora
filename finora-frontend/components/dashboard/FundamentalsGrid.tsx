import type { ReactNode } from "react";
import type { StockDetail } from "@/lib/api";
import { formatCurrency, formatNumber, formatVolume } from "@/lib/format";
import { TrendingUp, TrendingDown, BarChart2, DollarSign, Activity } from "lucide-react";

interface Props {
  stock: StockDetail;
}

interface MetricProps {
  label: string;
  value: string;
  sub?: string;
  accent?: "positive" | "negative" | "neutral";
  icon?: ReactNode;
}

function Metric({ label, value, sub, accent, icon }: MetricProps) {
  const accentClass =
    accent === "positive" ? "text-emerald-400" :
    accent === "negative" ? "text-rose-400" :
    "text-foreground";

  return (
    <div className="rounded-xl border border-border bg-card p-3.5 flex flex-col gap-1.5 hover:border-primary/30 hover:bg-muted/20 transition-all group">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">{label}</span>
        {icon && <span className="text-muted-foreground/40 group-hover:text-primary/50 transition-colors">{icon}</span>}
      </div>
      <span className={`text-sm font-bold font-mono ${accentClass}`}>{value}</span>
      {sub && <span className="text-[10px] text-muted-foreground/60">{sub}</span>}
    </div>
  );
}

export function FundamentalsGrid({ stock }: Props) {
  const currency = stock.currency === "INR" ? "INR" : "USD";

  const peAccent = stock.pe != null
    ? stock.pe > 40 ? "negative" : stock.pe < 15 ? "positive" : "neutral"
    : "neutral";

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center gap-2">
        <BarChart2 className="w-4 h-4 text-primary" />
        <h3 className="text-sm font-semibold text-foreground">Fundamentals</h3>
      </div>
      <div className="p-3 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5">
        <Metric
          label="Market Cap"
          value={formatCurrency(stock.market_cap, currency)}
          icon={<DollarSign className="w-3.5 h-3.5" />}
        />
        <Metric
          label="P/E Ratio"
          value={formatNumber(stock.pe)}
          accent={peAccent}
          icon={<Activity className="w-3.5 h-3.5" />}
        />
        <Metric
          label="Forward P/E"
          value={formatNumber(stock.forward_pe)}
          icon={<Activity className="w-3.5 h-3.5" />}
        />
        <Metric
          label="EPS (TTM)"
          value={stock.eps != null ? formatCurrency(stock.eps, currency) : "—"}
          icon={<DollarSign className="w-3.5 h-3.5" />}
        />
        <Metric
          label="Volume"
          value={formatVolume(stock.volume)}
          icon={<BarChart2 className="w-3.5 h-3.5" />}
        />
        <Metric
          label="Avg Vol (30d)"
          value={formatVolume(stock.avg_volume_30d)}
          icon={<BarChart2 className="w-3.5 h-3.5" />}
        />
        <Metric
          label="52W High"
          value={stock.week_52_high != null ? formatCurrency(stock.week_52_high, currency) : "—"}
          accent="positive"
          icon={<TrendingUp className="w-3.5 h-3.5" />}
        />
        <Metric
          label="52W Low"
          value={stock.week_52_low != null ? formatCurrency(stock.week_52_low, currency) : "—"}
          accent="negative"
          icon={<TrendingDown className="w-3.5 h-3.5" />}
        />
      </div>
    </div>
  );
}
