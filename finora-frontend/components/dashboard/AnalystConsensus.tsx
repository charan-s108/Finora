import { currencySymbol, formatCurrency } from "@/lib/format";

interface Consensus {
  buy: number;
  hold: number;
  sell: number;
  avg_target?: number | null;
}

interface Props {
  consensus: Consensus | null;
  currency?: string;
}

export function AnalystConsensus({ consensus, currency = "USD" }: Props) {
  if (!consensus) {
    return (
      <div className="card-dark p-4">
        <h3 className="text-sm font-semibold text-foreground mb-3">Analyst Consensus</h3>
        <p className="text-xs text-muted-foreground">No analyst data available</p>
      </div>
    );
  }

  const { buy, hold, sell, avg_target } = consensus;
  const total = buy + hold + sell || 1;
  const buyPct = Math.round((buy / total) * 100);
  const holdPct = Math.round((hold / total) * 100);
  const sellPct = 100 - buyPct - holdPct;

  const rating = buyPct >= 60 ? "Strong Buy" : buyPct >= 40 ? "Buy" : holdPct >= 50 ? "Hold" : "Sell";
  const ratingColor = buyPct >= 60 ? "text-emerald-400" : buyPct >= 40 ? "text-emerald-400" : holdPct >= 50 ? "text-yellow-400" : "text-rose-400";
  const sym = currencySymbol(currency);

  return (
    <div className="card-dark p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Analyst Consensus</h3>
        <span className={`text-xs font-semibold ${ratingColor}`}>{rating}</span>
      </div>

      {/* Stacked bar */}
      <div className="flex h-2 rounded-full overflow-hidden gap-0.5">
        {buyPct > 0 && <div className="bg-emerald-500 rounded-l-full" style={{ width: `${buyPct}%` }} />}
        {holdPct > 0 && <div className="bg-yellow-500" style={{ width: `${holdPct}%` }} />}
        {sellPct > 0 && <div className="bg-rose-500 rounded-r-full" style={{ width: `${sellPct}%` }} />}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-muted-foreground">Buy</span>
          <span className="font-semibold text-foreground font-mono">{buy}</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-yellow-500" />
          <span className="text-muted-foreground">Hold</span>
          <span className="font-semibold text-foreground font-mono">{hold}</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-rose-500" />
          <span className="text-muted-foreground">Sell</span>
          <span className="font-semibold text-foreground font-mono">{sell}</span>
        </div>
      </div>

      {avg_target != null && (
        <div className="flex items-center justify-between pt-1 border-t border-border">
          <span className="text-xs text-muted-foreground">Avg. Price Target</span>
          <span className="text-sm font-semibold font-mono text-foreground">
            {sym}{avg_target.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
      )}
    </div>
  );
}
