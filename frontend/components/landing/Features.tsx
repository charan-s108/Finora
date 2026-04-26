import { Brain, BarChart3, Clock, Shield, Globe2, TrendingUp } from "lucide-react";

const FEATURES = [
  {
    icon: Brain,
    title: "Multi-Layer RAG AI",
    description:
      "LangGraph orchestrates real-time data, 20-year OHLCV patterns, and live news simultaneously — fused into a single grounded response.",
    accent: "text-violet-500",
    bg: "bg-violet-500/10",
  },
  {
    icon: BarChart3,
    title: "Interactive Price Charts",
    description:
      "Recharts-powered candlestick and area charts with volume bars, 52-week range, and dynamic timeframe detection from natural language queries.",
    accent: "text-blue-500",
    bg: "bg-blue-500/10",
  },
  {
    icon: Clock,
    title: "Real-Time Intelligence",
    description:
      "Live quotes via Yahoo Finance with 5-minute intraday bars, pre/post market data, and volume anomaly detection.",
    accent: "text-emerald-500",
    bg: "bg-emerald-500/10",
  },
  {
    icon: Globe2,
    title: "NRI-First Design",
    description:
      "Covers US, Indian, and global equities in one platform. INR and USD support, SEBI/SEC disclaimers, NSE/BSE/NYSE/NASDAQ data.",
    accent: "text-orange-500",
    bg: "bg-orange-500/10",
  },
  {
    icon: Shield,
    title: "Financial Guardrails",
    description:
      "Llama-3.1-8b intent classifier blocks harmful queries. Output hallucination checks, PII scrub, and mandatory disclaimers.",
    accent: "text-red-500",
    bg: "bg-red-500/10",
  },
  {
    icon: TrendingUp,
    title: "20-Year Pattern RAG",
    description:
      "Qdrant vector search over 1,400+ historical event chunks. Semantic + BM25 hybrid retrieval with Cohere reranking.",
    accent: "text-primary",
    bg: "bg-primary/10",
  },
];

export function Features() {
  return (
    <section className="py-20 px-4 border-t border-border">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="font-heading font-bold text-3xl sm:text-4xl md:text-5xl text-foreground mb-4">
            Built for serious investors
          </h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Every feature is architected for institutional-grade analysis <br />
            — not just a chatbot on top of stocks.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map(({ icon: Icon, title, description, accent, bg }) => (
            <div
              key={title}
              className="group p-6 rounded-2xl border border-border bg-card hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 transition-all"
            >
              <div className={`w-11 h-11 rounded-xl ${bg} flex items-center justify-center mb-4`}>
                <Icon className={`w-5 h-5 ${accent}`} />
              </div>
              <h3 className="font-heading font-semibold text-lg text-foreground mb-2">{title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
