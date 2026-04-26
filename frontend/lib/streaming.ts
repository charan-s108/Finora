"use client";

export type SSEEventType =
  | "status"
  | "guardrail"
  | "intent"
  | "retrieving"
  | "token"
  | "citation"
  | "disclaimer"
  | "chart_data"
  | "done"
  | "error";

export interface SSEEvent {
  type: SSEEventType;
  [key: string]: unknown;
}

export interface PriceBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

export type UserMode = "insight" | "trader";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  isAutoSummary?: boolean;   // true for the opening narrative — no user bubble shown
  citations?: Array<{ url: string; title: string; time?: string }>;
  disclaimer?: string;
  confidence?: number;
  intents?: string[];
  isStreaming?: boolean;
  chartData?: { ticker: string; currency: string; label: string; bars: PriceBar[] };
  traceUrl?: string;
}

export async function* streamChat(
  query: string,
  ticker: string,
  conversationHistory: Array<{ role: string; content: string }>,
  sessionId: string,
  userMode: UserMode = "insight",
  signal?: AbortSignal
): AsyncGenerator<SSEEvent> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      ticker,
      conversation_history: conversationHistory,
      session_id: sessionId,
      user_mode: userMode,
    }),
    signal,
  });

  if (!res.ok || !res.body) {
    yield { type: "error", message: "Failed to connect to Finora AI" };
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const event = JSON.parse(line.slice(6)) as SSEEvent;
          yield event;
        } catch {
          // malformed SSE line, skip
        }
      }
    }
  }
}
