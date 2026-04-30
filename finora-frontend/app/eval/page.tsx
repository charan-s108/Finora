import Link from "next/link";
import Image from "next/image";
import { getEvalResults } from "@/lib/api";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { CheckCircle2, XCircle, FlaskConical, Clock, Database, BarChart3, AlertCircle } from "lucide-react";

export const metadata = {
  title: "RAG Evaluation — Finora",
  description: "RAGAS evaluation results for Finora AI retrieval pipeline",
};

const METRIC_LABELS: Record<string, { label: string; description: string }> = {
  faithfulness:      { label: "Faithfulness",      description: "Claims grounded in retrieved context" },
  answer_relevancy:  { label: "Answer Relevancy",  description: "Answer directly addresses the query" },
  context_recall:    { label: "Context Recall",    description: "Retrieved docs contain needed info" },
  context_precision: { label: "Context Precision", description: "Retrieved docs are on-topic" },
};

function ScoreBar({ score, target, passed }: { score: number; target: number; passed: boolean }) {
  const scorePct = Math.round(score * 100);
  const targetPct = Math.round(target * 100);

  return (
    <div className="relative h-3 bg-muted/40 rounded-full overflow-visible">
      {/* Fill */}
      <div
        className={`h-full rounded-full transition-all ${passed ? "bg-emerald-500/80" : "bg-rose-500/70"}`}
        style={{ width: `${scorePct}%` }}
      />
      {/* Target line */}
      <div
        className="absolute top-0 bottom-0 w-0.5 bg-yellow-400/70 rounded-full"
        style={{ left: `${targetPct}%` }}
        title={`Target: ${targetPct}%`}
      />
    </div>
  );
}

function MetricCard({
  metricKey,
  score,
  target,
  passed,
  delta,
}: {
  metricKey: string;
  score: number;
  target: number;
  passed: boolean;
  delta?: number;
}) {
  const info = METRIC_LABELS[metricKey] ?? { label: metricKey, description: "" };
  const scorePct = Math.round(score * 100);
  const targetPct = Math.round(target * 100);
  const deltaPct = delta != null ? Math.round(delta * 100) : Math.round((score - target) * 100);

  return (
    <div className={`rounded-xl border bg-card p-4 space-y-3 ${passed ? "border-emerald-500/20" : "border-rose-500/20"}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-foreground">{info.label}</p>
          <p className="text-[11px] text-muted-foreground mt-0.5">{info.description}</p>
        </div>
        {passed ? (
          <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
        ) : (
          <XCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
        )}
      </div>

      <ScoreBar score={score} target={target} passed={passed} />

      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-3">
          <span className={`font-mono font-bold text-base ${passed ? "text-emerald-400" : "text-rose-400"}`}>
            {scorePct}%
          </span>
          <span className="text-muted-foreground/60">
            target <span className="text-yellow-400 font-mono">{targetPct}%</span>
          </span>
        </div>
        <span className={`font-mono text-[11px] px-1.5 py-0.5 rounded font-semibold ${
          deltaPct >= 0
            ? "bg-emerald-500/10 text-emerald-400"
            : "bg-rose-500/10 text-rose-400"
        }`}>
          {deltaPct >= 0 ? "+" : ""}{deltaPct}pp
        </span>
      </div>
    </div>
  );
}

export default async function EvalPage() {
  const eval_data = await getEvalResults();

  const hasResults = eval_data && Object.keys(eval_data.results).length > 0;

  function formatRunAt(ts?: string | null) {
    if (!ts) return null;
    try {
      return new Intl.DateTimeFormat("en-US", {
        month: "short", day: "numeric", year: "numeric",
        hour: "2-digit", minute: "2-digit", timeZoneName: "short",
      }).format(new Date(ts));
    } catch { return ts; }
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Navbar */}
      <header className="sticky top-0 z-50 border-b border-border/50 bg-transparent backdrop-blur-md">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity flex-shrink-0">
            <Image src="/finora_logo.png" alt="Finora" width={88} height={24} className="h-6 w-auto" />
          </Link>
          <span className="text-border hidden sm:block">|</span>
          <div className="flex items-center gap-1.5 hidden sm:flex">
            <FlaskConical className="w-3.5 h-3.5 text-primary" />
            <span className="text-sm font-semibold text-foreground">RAG Evaluation</span>
          </div>
          <div className="flex-1" />
          <Link href="/dashboard" className="text-xs text-muted-foreground hover:text-foreground transition-colors">
            Dashboard →
          </Link>
          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-8 space-y-6">

        {/* Page header */}
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-foreground">RAGAS Evaluation</h1>
            {hasResults && (
              <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${
                eval_data.overall_pass
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  : "bg-rose-500/10 text-rose-400 border-rose-500/20"
              }`}>
                {eval_data.overall_pass ? "ALL PASS" : "NEEDS WORK"}
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            Automated quality measurement of Finora AI&apos;s retrieval-augmented generation pipeline.
          </p>
        </div>

        {/* Meta strip */}
        {hasResults && (
          <div className="flex flex-wrap gap-4 text-[11px] text-muted-foreground">
            {eval_data.run_at && (
              <div className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                Last run: <span className="text-foreground font-medium">{formatRunAt(eval_data.run_at)}</span>
              </div>
            )}
            {eval_data.n_pairs && (
              <div className="flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5" />
                <span className="text-foreground font-medium">{eval_data.n_pairs}</span> synthetic QA pairs
              </div>
            )}
            {eval_data.tickers?.length && (
              <div className="flex items-center gap-1.5">
                <BarChart3 className="w-3.5 h-3.5" />
                Tickers: <span className="text-foreground font-medium font-mono">{eval_data.tickers.join(", ")}</span>
              </div>
            )}
          </div>
        )}

        {/* No data state */}
        {!hasResults && (
          <div className="rounded-xl border border-border bg-card p-10 flex flex-col items-center gap-4 text-center">
            <AlertCircle className="w-10 h-10 text-muted-foreground/30" />
            <div>
              <p className="font-semibold text-foreground">No evaluation results yet</p>
              <p className="text-sm text-muted-foreground mt-1">Run the eval script to generate results.</p>
            </div>
            <div className="rounded-lg bg-muted/40 border border-border px-4 py-3 text-left w-full max-w-md">
              <p className="text-[11px] text-muted-foreground mb-1 font-medium uppercase tracking-wide">Run from backend/</p>
              <code className="text-xs font-mono text-foreground whitespace-pre-wrap">
                {`python backend/scripts/eval_rag.py \\\n  --tickers AAPL RELIANCE INFY META \\\n  --collection historical --n 3`}
              </code>
            </div>
          </div>
        )}

        {/* Metrics grid */}
        {hasResults && (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {Object.entries(eval_data.results).map(([key, metric]) => (
                <MetricCard
                  key={key}
                  metricKey={key}
                  score={metric.score}
                  target={metric.target}
                  passed={metric.passed}
                  delta={metric.delta}
                />
              ))}
            </div>

            {/* Overall summary card */}
            <div className={`rounded-xl border p-5 flex flex-col sm:flex-row items-start sm:items-center gap-4 ${
              eval_data.overall_pass
                ? "border-emerald-500/30 bg-emerald-500/5"
                : "border-rose-500/30 bg-rose-500/5"
            }`}>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  {eval_data.overall_pass
                    ? <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    : <XCircle className="w-5 h-5 text-rose-400" />
                  }
                  <span className={`font-bold text-base ${eval_data.overall_pass ? "text-emerald-400" : "text-rose-400"}`}>
                    {eval_data.overall_pass ? "Pipeline meets quality targets" : "Pipeline below quality targets"}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground ml-7">
                  {eval_data.overall_pass
                    ? "All RAGAS metrics passed. RAG pipeline is production-ready."
                    : "One or more metrics missed target. Review retrieval quality or increase training data."}
                </p>
              </div>

              {/* Pass count */}
              <div className="text-right flex-shrink-0">
                <span className="text-3xl font-bold font-mono text-foreground">
                  {Object.values(eval_data.results).filter(m => m.passed).length}
                  <span className="text-lg text-muted-foreground">/{Object.values(eval_data.results).length}</span>
                </span>
                <p className="text-[11px] text-muted-foreground">metrics passed</p>
              </div>
            </div>

            {/* Legend */}
            <div className="flex items-center gap-4 text-[11px] text-muted-foreground px-1">
              <div className="flex items-center gap-1.5">
                <div className="w-8 h-1.5 rounded-full bg-emerald-500/80" />
                Score
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-0.5 h-3 bg-yellow-400/70 rounded-full" />
                Target threshold
              </div>
              <div className="flex items-center gap-1.5">
                <span className="font-mono text-[10px] bg-emerald-500/10 text-emerald-400 px-1 rounded">+Xpp</span>
                Delta from target
              </div>
            </div>
          </>
        )}

        {/* Methodology note */}
        <div className="rounded-xl border border-border/50 bg-muted/10 p-4 space-y-2">
          <p className="text-xs font-semibold text-foreground">Methodology</p>
          <p className="text-[11px] text-muted-foreground leading-relaxed">
            Synthetic QA pairs generated from Qdrant corpus chunks via <span className="text-foreground font-mono">llama-3.1-8b-instant</span>.
            Evaluation performed by <span className="text-foreground font-mono">RAGAS 0.4</span> using the same model + <span className="text-foreground font-mono">all-MiniLM-L6-v2</span> embeddings.
            Historical collection sampled — 20yr OHLCV event chunks across US + Indian equities.
          </p>
        </div>
      </main>

      <footer className="border-t border-border/40 bg-background/60 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-4 h-10 flex items-center justify-center">
          <p className="text-[11px] text-muted-foreground/50 text-center">
            © {new Date().getFullYear()} Finora · For informational purposes only · Not financial advice
          </p>
        </div>
      </footer>
    </div>
  );
}
