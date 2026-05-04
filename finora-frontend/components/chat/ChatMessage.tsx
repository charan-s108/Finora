"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ExternalLink, Sparkles } from "lucide-react";
import { FinoraIcon } from "@/components/ui/FinoraIcon";
import type { ChatMessage as ChatMessageType, FinanceBar } from "@/lib/streaming";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

interface Props {
  message: ChatMessageType;
}

function formatCitationTime(time: string | undefined): string {
  if (!time) return "";
  const date = new Date(time);
  if (isNaN(date.getTime())) return time;
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

const OrderedContext = React.createContext(false);

function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => (
          <p className="mb-1.5 last:mb-0 leading-relaxed">{children}</p>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-primary/90 tracking-wide">{children}</strong>
        ),
        ul: ({ children }) => (
          <OrderedContext.Provider value={false}>
            <ul className="mb-2 space-y-1 pl-3">{children}</ul>
          </OrderedContext.Provider>
        ),
        ol: ({ children }) => (
          <OrderedContext.Provider value={true}>
            <ol className="mb-2 space-y-1 pl-5 list-decimal [&>li]:list-item">{children}</ol>
          </OrderedContext.Provider>
        ),
        li: ({ children }) => {
          // eslint-disable-next-line react-hooks/rules-of-hooks
          const isOrdered = React.useContext(OrderedContext);
          if (isOrdered) {
            return (
              <li className="text-sm leading-relaxed marker:text-muted-foreground/70">
                {children}
              </li>
            );
          }
          return (
            <li className="flex gap-2 text-sm leading-relaxed list-none">
              <span className="text-primary mt-1.5 flex-shrink-0">•</span>
              <span>{children}</span>
            </li>
          );
        },
        h2: ({ children }) => (
          <h2 className="text-sm font-semibold text-foreground mb-1.5 mt-3 first:mt-0 border-b border-border pb-1">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-1.5 mt-3 first:mt-0 border-b border-border pb-1">
            {children}
          </h3>
        ),
        h4: ({ children }) => (
          <h4 className="text-xs font-semibold text-foreground mb-1 mt-2">{children}</h4>
        ),
        table: ({ children }) => (
          <div className="my-2 rounded-lg overflow-hidden border border-border">
            <table className="w-full text-xs">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-muted/50">{children}</thead>
        ),
        th: ({ children }) => (
          <th className="px-3 py-2 text-left font-semibold text-muted-foreground">{children}</th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-2 border-t border-border font-mono">{children}</td>
        ),
        code: ({ children }) => (
          <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono text-primary">{children}</code>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-primary pl-3 my-2 text-muted-foreground italic text-xs">
            {children}
          </blockquote>
        ),
        hr: () => <hr className="border-border my-2" />,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

function PriceChart({ chartData }: { chartData: NonNullable<ChatMessageType["chartData"]> }) {
  const { bars, ticker, currency, label } = chartData;
  if (!bars.length) return null;

  const first = bars[0].close;
  const last = bars[bars.length - 1].close;
  const isPositive = last >= first;
  const color = isPositive ? "#22c55e" : "#ef4444";
  const sym = currency === "INR" ? "₹" : "$";

  const min = Math.min(...bars.map(b => b.low));
  const max = Math.max(...bars.map(b => b.high));
  const pad = (max - min) * 0.08;

  return (
    <div className="mt-2 rounded-lg border border-border bg-background/50 p-2.5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">{ticker} · {label}</span>
        <span className={`text-xs font-mono font-semibold ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
          {sym}{last.toFixed(2)}
          <span className="text-[10px] ml-1 opacity-70">
            {isPositive ? "▲" : "▼"} {Math.abs(((last - first) / first) * 100).toFixed(2)}%
          </span>
        </span>
      </div>
      <ResponsiveContainer width="100%" height={80}>
        <AreaChart data={bars} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
          <defs>
            <linearGradient id={`grad-${ticker}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" hide />
          <YAxis domain={[min - pad, max + pad]} hide />
          <Tooltip
            contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 11 }}
            formatter={(val: number) => [`${sym}${val.toFixed(2)}`, "Close"]}
            labelFormatter={(lbl: string) => lbl}
          />
          <Area
            type="monotone"
            dataKey="close"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#grad-${ticker})`}
            dot={false}
            activeDot={{ r: 3, fill: color }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function FinanceBarChart({ financeChartData }: { financeChartData: NonNullable<ChatMessageType["financeChartData"]> }) {
  const { bars, currency } = financeChartData;
  if (!bars.length) return null;
  const sym = currency === "INR" ? "₹" : "$";

  return (
    <div className="mt-2 rounded-lg border border-border bg-background/50 p-2.5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Revenue & Net Income (Billions)</span>
        <span className="text-[10px] text-muted-foreground/60">{sym}B</span>
      </div>
      <ResponsiveContainer width="100%" height={100}>
        <BarChart data={bars} margin={{ top: 2, right: 4, left: 4, bottom: 2 }} barGap={2}>
          <XAxis dataKey="period" tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
          <YAxis hide />
          <Tooltip
            contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 11 }}
            formatter={(val: number, name: string) => [`${sym}${val}B`, name === "revenue" ? "Revenue" : "Net Income"]}
          />
          <Bar dataKey="revenue" fill="hsl(var(--primary))" opacity={0.7} radius={[3, 3, 0, 0]} maxBarSize={28} />
          <Bar dataKey="net_income" fill="#22c55e" opacity={0.8} radius={[3, 3, 0, 0]} maxBarSize={28} />
        </BarChart>
      </ResponsiveContainer>
      <div className="flex gap-3 mt-1.5 justify-end">
        <span className="flex items-center gap-1 text-[9px] text-muted-foreground">
          <span className="w-2 h-2 rounded-sm bg-primary/70 inline-block" />Revenue
        </span>
        <span className="flex items-center gap-1 text-[9px] text-muted-foreground">
          <span className="w-2 h-2 rounded-sm bg-emerald-500/80 inline-block" />Net Income
        </span>
      </div>
    </div>
  );
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-[92%] ${isUser ? "order-2" : "order-1"}`}>
        {!isUser && (
          <div className="flex items-center gap-1.5 mb-1.5 flex-wrap">
            <div className="w-4 h-4 rounded bg-primary flex items-center justify-center flex-shrink-0">
              <FinoraIcon size={10} className="text-primary-foreground" />
            </div>
            <span className="text-xs text-muted-foreground font-medium">Finora AI</span>
            {message.isAutoSummary && (
              <span className="flex items-center gap-0.5 text-[10px] text-primary/60 bg-primary/5 px-1.5 py-0.5 rounded-full border border-primary/10">
                <Sparkles className="w-2.5 h-2.5" />
                Auto-summary
              </span>
            )}
            {message.intents && message.intents.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {message.intents.slice(0, 2).map(intent => (
                  <span key={intent} className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-full">
                    {intent.replace("_", " ")}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        <div className={`rounded-xl px-3 py-2.5 text-sm ${
          isUser
            ? "bg-primary text-primary-foreground rounded-br-sm"
            : "bg-secondary text-foreground rounded-bl-sm border border-border"
        }`}>
          {isUser ? (
            <span className="whitespace-pre-wrap leading-relaxed">{message.content}</span>
          ) : message.isStreaming && !message.content ? (
            <span className="opacity-40 text-xs">Analyzing...</span>
          ) : (
            <>
              <MarkdownContent content={message.content || ""} />
              {message.chartData && <PriceChart chartData={message.chartData} />}
              {message.financeChartData && <FinanceBarChart financeChartData={message.financeChartData} />}
            </>
          )}
        </div>

        {message.citations && message.citations.length > 0 && (
          <div className="mt-2 space-y-1">
            {message.citations.slice(0, 4).map((c, i) => (
              <a
                key={i}
                href={c.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors group"
              >
                <ExternalLink className="w-3 h-3 flex-shrink-0 opacity-50 group-hover:opacity-100" />
                <span className="truncate flex-1">{c.title}</span>
                <span className="flex items-center gap-1 flex-shrink-0 text-[10px] text-muted-foreground/50">
                  {c.source && <span>{c.source}</span>}
                  {c.source && c.time && <span>·</span>}
                  {c.time && <span>{formatCitationTime(c.time)}</span>}
                </span>
              </a>
            ))}
          </div>
        )}

        {!isUser && (message.confidence != null || message.traceUrl) && (
          <div className="mt-1 flex items-center justify-between gap-2">
            {message.confidence != null && message.confidence < 0.5 && (
              <span className="text-[10px] text-muted-foreground/60">
                Confidence: {Math.round(message.confidence * 100)}%
              </span>
            )}
            {message.traceUrl && (
              <a
                href={message.traceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto flex items-center gap-1 text-[10px] text-muted-foreground/50 hover:text-primary transition-colors"
              >
                <ExternalLink className="w-2.5 h-2.5" />
                LangSmith trace
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
