"use client";

interface SectorData {
  sector: string;
  return_pct: number;
}

interface Props {
  data?: SectorData[];
}

const MOCK_SECTORS: SectorData[] = [
  { sector: "Technology", return_pct: 1.4 },
  { sector: "Healthcare", return_pct: -0.8 },
  { sector: "Financials", return_pct: 0.6 },
  { sector: "Energy", return_pct: -1.2 },
  { sector: "Consumer", return_pct: 0.3 },
  { sector: "Materials", return_pct: -0.5 },
  { sector: "Industrials", return_pct: 0.9 },
  { sector: "Utilities", return_pct: -0.2 },
];

function pctToColor(pct: number): string {
  if (pct > 1.5) return "bg-emerald-500/80 text-emerald-50";
  if (pct > 0.5) return "bg-emerald-500/40 text-emerald-300";
  if (pct > 0) return "bg-emerald-500/20 text-emerald-400";
  if (pct > -0.5) return "bg-rose-500/20 text-rose-400";
  if (pct > -1.5) return "bg-rose-500/40 text-rose-300";
  return "bg-rose-500/80 text-rose-50";
}

export function SectorHeatmap({ data }: Props) {
  const sectors = data?.length ? data : MOCK_SECTORS;
  return (
    <div className="card-dark p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Sector Performance</h3>
        {!data?.length && (
          <span className="text-[10px] text-muted-foreground/50">sample data</span>
        )}
      </div>
      <div className="grid grid-cols-4 gap-1.5">
        {sectors.map(s => (
          <div key={s.sector} className={`rounded-lg p-2 text-center ${pctToColor(s.return_pct)}`}>
            <div className="text-[10px] font-medium leading-tight">{s.sector}</div>
            <div className="text-xs font-bold font-mono mt-0.5">
              {s.return_pct >= 0 ? "+" : ""}{s.return_pct.toFixed(1)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
