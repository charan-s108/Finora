"use client";

import { useRef } from "react";
import { motion, useInView, type Variants } from "framer-motion";
import { Brain, BarChart3, Clock, Shield, Globe2, TrendingUp } from "lucide-react";

const STATS = [
  { value: "555+", label: "Global Stocks", sub: "US · India · 15+ exchanges" },
  { value: "20yr", label: "Deep History", sub: "Weekly OHLCV per ticker" },
  { value: "1,400+", label: "RAG Vectors", sub: "Historical event chunks" },
  { value: "3", label: "RAG Layers", sub: "Fused in real time" },
  { value: "<500ms", label: "AI Latency", sub: "Intent to grounded answer" },
];

const FEATURES = [
  {
    icon: Brain,
    num: "01",
    title: "Multi-Layer RAG AI",
    description:
      "LangGraph orchestrates real-time quotes, 20-year OHLCV patterns, and live news simultaneously — fused into one grounded response with source citations.",
    tags: ["LangGraph", "Groq", "Qdrant"],
    colorClass: "text-violet-400 dark:text-violet-400",
    bgClass: "bg-violet-500/10",
    glowClass: "hover:shadow-violet-500/10",
    borderGlow: "hover:border-violet-500/40",
    gradientClass: "from-violet-500/8 via-transparent to-transparent",
    span2: true,
  },
  {
    icon: Clock,
    num: "02",
    title: "Real-Time Intelligence",
    description:
      "Live quotes with 5-minute intraday bars, pre/post-market data, and volume anomaly detection across US & Indian markets.",
    tags: ["Yahoo Finance", "< 500ms"],
    colorClass: "text-emerald-400",
    bgClass: "bg-emerald-500/10",
    glowClass: "hover:shadow-emerald-500/10",
    borderGlow: "hover:border-emerald-500/40",
    gradientClass: "from-emerald-500/8 via-transparent to-transparent",
    span2: false,
  },
  {
    icon: BarChart3,
    num: "03",
    title: "Interactive Price Charts",
    description:
      "Candlestick and area charts with volume bars, 52-week range overlay, and dynamic timeframe detection straight from natural language queries.",
    tags: ["Recharts", "OHLCV", "NLP"],
    colorClass: "text-blue-400",
    bgClass: "bg-blue-500/10",
    glowClass: "hover:shadow-blue-500/10",
    borderGlow: "hover:border-blue-500/40",
    gradientClass: "from-blue-500/8 via-transparent to-transparent",
    span2: false,
  },
  {
    icon: TrendingUp,
    num: "04",
    title: "20-Year Pattern RAG",
    description:
      "Qdrant vector search over 1,400+ historical event chunks. Semantic + BM25 hybrid retrieval with Cohere reranking surfaces patterns invisible to standard search.",
    tags: ["Qdrant", "BM25 Hybrid", "Cohere Rerank"],
    colorClass: "text-primary",
    bgClass: "bg-primary/10",
    glowClass: "hover:shadow-primary/10",
    borderGlow: "hover:border-primary/40",
    gradientClass: "from-primary/8 via-transparent to-transparent",
    span2: true,
  },
  {
    icon: Globe2,
    num: "05",
    title: "NRI-First Design",
    description:
      "US, Indian, and global equities in one platform. INR & USD, SEBI/SEC disclaimers, NSE/BSE/NYSE/NASDAQ — built for the global diaspora investor.",
    tags: ["INR · USD", "SEBI · SEC"],
    colorClass: "text-orange-400",
    bgClass: "bg-orange-500/10",
    glowClass: "hover:shadow-orange-500/10",
    borderGlow: "hover:border-orange-500/40",
    gradientClass: "from-orange-500/8 via-transparent to-transparent",
    span2: false,
  },
  {
    icon: Shield,
    num: "06",
    title: "Financial Guardrails",
    description:
      "Llama-3.1-8b intent classifier blocks harmful queries. Output hallucination checks, PII scrub, and mandatory regulatory disclaimers on every response.",
    tags: ["Llama 3.1-8b", "SEBI · SEC"],
    colorClass: "text-rose-400",
    bgClass: "bg-rose-500/10",
    glowClass: "hover:shadow-rose-500/10",
    borderGlow: "hover:border-rose-500/40",
    gradientClass: "from-rose-500/8 via-transparent to-transparent",
    span2: false,
  },
];

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, delay: i * 0.07, ease: [0.22, 1, 0.36, 1] },
  }),
};

export function Features() {
  const statsRef = useRef(null);
  const statsVisible = useInView(statsRef, { once: true, margin: "-60px" });

  const gridRef = useRef(null);
  const gridVisible = useInView(gridRef, { once: true, margin: "-80px" });

  return (
    <>
      {/* ── Stats trust bar ───────────────────────────────────── */}
      <section
        ref={statsRef}
        className="relative border-y border-border overflow-hidden py-12 px-4"
      >
        {/* subtle background */}
        <div className="absolute inset-0 bg-gradient-to-b from-card/60 to-background/40 pointer-events-none" />
        <div className="relative max-w-6xl mx-auto grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-8 lg:gap-0 lg:divide-x divide-border">
          {STATS.map(({ value, label, sub }, i) => (
            <motion.div
              key={label}
              custom={i}
              variants={fadeUp}
              initial="hidden"
              animate={statsVisible ? "show" : "hidden"}
              className="flex flex-col items-center text-center lg:px-8 gap-1"
            >
              <span className="font-heading font-black text-2xl sm:text-3xl text-gradient leading-none">
                {value}
              </span>
              <span className="text-sm font-semibold text-foreground mt-0.5">{label}</span>
              <span className="text-[11px] text-muted-foreground leading-snug">{sub}</span>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Feature bento grid ───────────────────────────────── */}
      <section className="py-24 px-4 relative overflow-hidden">
        {/* radial glow background */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[600px] bg-primary/5 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-7xl mx-auto">
          {/* Section header */}
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          >
            <p className="text-xs font-bold text-primary uppercase tracking-[0.22em] mb-4">
              Architecture
            </p>
            <h2 className="font-heading font-black text-4xl sm:text-5xl md:text-6xl text-foreground mb-5 leading-[1.05] tracking-tight">
              Built for serious{" "}
              <span className="text-gradient">investors</span>
            </h2>
            <p className="text-muted-foreground text-lg max-w-xl mx-auto leading-relaxed">
              Every layer is engineered for institutional-grade analysis —<br className="hidden sm:block" />
              not a chatbot bolted on top of stock prices.
            </p>
          </motion.div>

          {/* Bento grid */}
          <div
            ref={gridRef}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          >
            {FEATURES.map(
              (
                {
                  icon: Icon,
                  num,
                  title,
                  description,
                  tags,
                  colorClass,
                  bgClass,
                  glowClass,
                  borderGlow,
                  gradientClass,
                  span2,
                },
                i
              ) => (
                <motion.div
                  key={title}
                  custom={i}
                  variants={fadeUp}
                  initial="hidden"
                  animate={gridVisible ? "show" : "hidden"}
                  className={`group relative rounded-2xl border border-border bg-card overflow-hidden cursor-default transition-all duration-300 hover:shadow-xl ${glowClass} ${borderGlow} ${
                    span2 ? "md:col-span-2 lg:col-span-2" : ""
                  }`}
                >
                  {/* Hover gradient wash */}
                  <div
                    className={`absolute inset-0 bg-gradient-to-br ${gradientClass} opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none`}
                  />

                  {/* Top accent line that fills on hover */}
                  <div
                    className={`absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-current to-transparent opacity-0 group-hover:opacity-40 transition-opacity duration-500 ${colorClass}`}
                  />

                  <div className="relative p-6 flex flex-col h-full gap-5">
                    {/* Icon + number row */}
                    <div className="flex items-start justify-between">
                      <div
                        className={`w-12 h-12 rounded-2xl ${bgClass} flex items-center justify-center flex-shrink-0 transition-transform duration-300 group-hover:scale-110`}
                      >
                        <Icon className={`w-5 h-5 ${colorClass}`} />
                      </div>
                      <span className="font-mono text-xs font-bold text-muted-foreground/30 group-hover:text-muted-foreground/50 transition-colors select-none">
                        {num}
                      </span>
                    </div>

                    {/* Text */}
                    <div className="flex-1 space-y-2">
                      <h3 className="font-heading font-bold text-xl text-foreground leading-snug tracking-tight">
                        {title}
                      </h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
                    </div>

                    {/* Tech badge pills */}
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {tags.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center text-[11px] font-mono font-semibold px-2.5 py-1 rounded-full bg-muted/50 text-muted-foreground border border-border/60 group-hover:border-border transition-colors"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </motion.div>
              )
            )}
          </div>
        </div>
      </section>
    </>
  );
}
