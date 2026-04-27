import { History, TrendingUp, TrendingDown, Calendar, Zap } from "lucide-react";

interface Signal {
  text?: string;
  date_range?: string;
  event_type?: string;
  return_pct?: number | null;
}

interface Props {
  signals: Signal[];
}

const EVENT_META: Record<string, { label: string; color: string; bg: string; border: string }> = {
  unusual_volume:   { label: "Volume Spike",      color: "text-amber-400",   bg: "bg-amber-500/10",   border: "border-amber-500/20" },
  macro_shock:      { label: "Macro Shock",        color: "text-rose-400",    bg: "bg-rose-500/10",    border: "border-rose-500/20" },
  sector_rotation:  { label: "Sector Rotation",    color: "text-blue-400",    bg: "bg-blue-500/10",    border: "border-blue-500/20" },
  earnings_week:    { label: "Earnings Week",       color: "text-violet-400",  bg: "bg-violet-500/10",  border: "border-violet-500/20" },
  fed_meeting:      { label: "Fed Meeting",         color: "text-orange-400",  bg: "bg-orange-500/10",  border: "border-orange-500/20" },
};

function getEventMeta(type?: string) {
  if (!type) return { label: "Event", color: "text-muted-foreground", bg: "bg-muted", border: "border-border" };
  return EVENT_META[type] ?? { label: type.replace(/_/g, " "), color: "text-primary", bg: "bg-primary/10", border: "border-primary/20" };
}

export function HistoricalRagPanel({ signals }: Props) {
  const displayed = signals.slice(0, 5);

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-muted/30">
        <div className="w-6 h-6 rounded-md bg-primary/10 flex items-center justify-center">
          <History className="w-3.5 h-3.5 text-primary" />
        </div>
        <h3 className="text-sm font-semibold text-foreground">Historical Patterns</h3>
        <span className="ml-auto text-[10px] font-medium bg-primary/10 text-primary px-2 py-0.5 rounded-full border border-primary/20">
          {displayed.length} events
        </span>
      </div>

      {displayed.length === 0 ? (
        <div className="px-4 py-8 text-center">
          <History className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
          <p className="text-xs text-muted-foreground">No historical patterns ingested yet</p>
        </div>
      ) : (
        <ul className="divide-y divide-border">
          {displayed.map((s, i) => {
            const meta = getEventMeta(s.event_type);
            const up = s.return_pct != null && s.return_pct >= 0;

            return (
              <li key={i} className="px-4 py-3 space-y-2 hover:bg-muted/20 transition-colors">
                {/* Event type + return */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${meta.bg} ${meta.color} ${meta.border}`}>
                    <Zap className="w-2.5 h-2.5" />
                    {meta.label}
                  </span>
                  {s.return_pct != null && (
                    <span className={`inline-flex items-center gap-0.5 text-xs font-bold font-mono px-2 py-0.5 rounded-full border ${
                      up
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                        : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                    }`}>
                      {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                      {up ? "+" : ""}{s.return_pct.toFixed(1)}% 10d fwd
                    </span>
                  )}
                </div>

                {/* Date range */}
                {s.date_range && (
                  <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                    <Calendar className="w-3 h-3" />
                    {s.date_range}
                  </div>
                )}

                {/* Full description */}
                {s.text && (
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {s.text}
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
