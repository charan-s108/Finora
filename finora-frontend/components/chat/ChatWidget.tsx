"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { X, AlertTriangle } from "lucide-react";
import { FinoraIcon } from "@/components/ui/FinoraIcon";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { SuggestionChips } from "./SuggestionChips";
import { TypingIndicator } from "./TypingIndicator";
import { streamChat, type ChatMessage as ChatMessageType, type PriceBar, type FinanceBar, type UserMode } from "@/lib/streaming";

interface Props {
  ticker: string;
}

export function ChatWidget({ ticker }: Props) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [userMode, setUserMode] = useState<UserMode>("insight");
  const [sessionId] = useState(() => crypto.randomUUID());
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController>();

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }, 50);
  }, []);

  const sendMessage = useCallback(async (
    query: string,
    opts: { isAutoSummary?: boolean; skipUserBubble?: boolean } = {}
  ) => {
    if (!query.trim() || streaming) return;

    const assistantMsg: ChatMessageType = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      isStreaming: true,
      isAutoSummary: opts.isAutoSummary,
    };

    if (opts.skipUserBubble) {
      setMessages(prev => [...prev, assistantMsg]);
    } else {
      const userMsg: ChatMessageType = {
        id: crypto.randomUUID(),
        role: "user",
        content: query,
      };
      setMessages(prev => [...prev, userMsg, assistantMsg]);
    }

    setInput("");
    setStreaming(true);

    const history = messages
      .filter(m => !m.isStreaming && !m.isAutoSummary)
      .map(m => ({ role: m.role, content: m.content }));

    abortRef.current = new AbortController();

    try {
      let content = "";
      let citations: ChatMessageType["citations"] = [];
      let disclaimer = "";
      let confidence = 0;
      let intents: string[] = [];
      let chartData: ChatMessageType["chartData"] | undefined;
      let financeChartData: ChatMessageType["financeChartData"] | undefined;
      let followupSuggestions: string[] | undefined;
      let traceUrl: string | undefined;

      for await (const event of streamChat(
        query, ticker, history, sessionId, userMode, abortRef.current.signal
      )) {
        if (event.type === "token") {
          content += (event.content as string) || "";
          setMessages(prev => prev.map(m =>
            m.id === assistantMsg.id ? { ...m, content, isStreaming: true } : m
          ));
          scrollToBottom();
        } else if (event.type === "chart_data") {
          chartData = {
            ticker: (event.ticker as string) || ticker,
            currency: (event.currency as string) || "USD",
            label: (event.label as string) || "1M",
            bars: (event.bars as PriceBar[]) || [],
          };
        } else if (event.type === "finance_chart") {
          financeChartData = {
            ticker: (event.ticker as string) || ticker,
            currency: (event.currency as string) || "USD",
            bars: (event.bars as FinanceBar[]) || [],
          };
        } else if (event.type === "suggestions") {
          followupSuggestions = (event.questions as string[]) || [];
        } else if (event.type === "intent") {
          intents = (event.intents as string[]) || [];
        } else if (event.type === "citation") {
          citations = (event.sources as ChatMessageType["citations"]) || [];
        } else if (event.type === "disclaimer") {
          disclaimer = (event.text as string) || "";
        } else if (event.type === "done") {
          confidence = (event.confidence as number) || 0;
          if (event.langsmith_url) traceUrl = event.langsmith_url as string;
        }
      }

      setMessages(prev => prev.map(m =>
        m.id === assistantMsg.id
          ? { ...m, content, citations, disclaimer, confidence, intents, chartData, financeChartData, followupSuggestions, traceUrl, isStreaming: false }
          : m
      ));
    } catch (err: unknown) {
      if ((err as Error)?.name === "AbortError") return;
      setMessages(prev => prev.map(m =>
        m.id === assistantMsg.id
          ? { ...m, content: "Something went wrong. Please try again.", isStreaming: false }
          : m
      ));
    } finally {
      setStreaming(false);
      scrollToBottom();
    }
  }, [messages, streaming, ticker, sessionId, userMode, scrollToBottom]);

  useEffect(() => {
    if (open) scrollToBottom();
  }, [open, messages, scrollToBottom]);

  const showChips = messages.length === 0 || (messages.length === 1 && !streaming);

  return (
    <>
      {/* FAB */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-primary shadow-lg shadow-primary/30 hover:bg-primary/90 transition-all hover:scale-105 flex items-center justify-center z-40 group"
          aria-label="Open Finora AI"
        >
          <FinoraIcon size={28} className="text-primary-foreground" />
          <span className="absolute -top-10 right-0 bg-card border border-border text-foreground text-xs px-2.5 py-1 rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
            Finora AI
          </span>
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-6 right-6 w-[390px] max-h-[620px] bg-card border border-border rounded-2xl shadow-2xl flex flex-col z-40 overflow-hidden">
          {/* Panel header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-card">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center overflow-hidden">
                <FinoraIcon size={18} className="text-primary-foreground" />
              </div>
              <div>
                <span className="text-sm font-semibold text-foreground">Finora AI</span>
                {ticker && <span className="text-xs text-muted-foreground ml-1.5">· {ticker}</span>}
              </div>
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 ml-1 animate-pulse" />
            </div>
            <div className="flex items-center gap-2">
              {/* Mode badge */}
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium border ${
                userMode === "trader"
                  ? "bg-orange-500/10 text-orange-400 border-orange-500/30"
                  : "bg-primary/10 text-primary border-primary/20"
              }`}>
                {userMode === "trader" ? "Trader" : "Insight"}
              </span>
              <button
                onClick={() => setOpen(false)}
                className="p-1.5 rounded-lg hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto overflow-x-hidden p-3 space-y-1 min-h-[200px]">
            {messages.length === 0 && !streaming && (
              <div className="flex flex-col items-center justify-center h-28 gap-2 text-center">
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <FinoraIcon size={18} className="text-primary" />
                </div>
                <p className="text-xs text-muted-foreground px-4">
                  Click <span className="text-foreground font-medium">Summarize this stock</span> below for a full analysis, or ask anything directly.
                </p>
              </div>
            )}
            {messages.map((msg, idx) => (
              <div key={msg.id}>
                <ChatMessage message={msg} />
                {!msg.isStreaming && msg.role === "assistant" && msg.followupSuggestions && msg.followupSuggestions.length > 0 && idx === messages.length - 1 && (
                  <div className="mt-2 flex flex-col gap-1.5 pl-1">
                    {msg.followupSuggestions.map((q, i) => (
                      <button
                        key={i}
                        onClick={() => sendMessage(q)}
                        disabled={streaming}
                        className="text-left text-xs text-muted-foreground hover:text-primary border border-border/50 hover:border-primary/30 rounded-lg px-2.5 py-1.5 transition-colors bg-secondary/30 hover:bg-primary/5 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {streaming && (
              <TypingIndicator />
            )}
          </div>

          {/* Suggestion chips — show after auto-summary finishes */}
          {showChips && !streaming && (
            <SuggestionChips ticker={ticker} onSelect={q => sendMessage(q)} />
          )}

          {/* Disclaimer footer */}
          {messages.some(m => m.role === "assistant") && (
            <div className="px-3 py-1.5 border-t border-border/50 flex items-center gap-1.5">
              <AlertTriangle className="w-3 h-3 text-yellow-400/70 flex-shrink-0" />
              <span className="text-[10px] text-muted-foreground/60 leading-tight">
                For informational purposes only. Not financial advice. Consult a registered advisor.
              </span>
            </div>
          )}

          {/* Input */}
          <ChatInput
            value={input}
            onChange={setInput}
            onSubmit={() => sendMessage(input)}
            disabled={streaming}
            userMode={userMode}
            onModeChange={setUserMode}
          />
        </div>
      )}
    </>
  );
}
