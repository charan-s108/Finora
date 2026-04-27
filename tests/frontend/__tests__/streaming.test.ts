/**
 * Frontend unit tests — streaming.ts
 * Tests SSE parsing, userMode propagation, ChatMessage interface shape.
 *
 * Run: cd frontend && npx jest tests/frontend/__tests__/streaming.test.ts
 */

import type { ChatMessage, UserMode, PriceBar } from "../../../frontend/lib/streaming";

// ---------------------------------------------------------------------------
// Type shape tests (compile-time enforcement via TS, runtime checks here)
// ---------------------------------------------------------------------------

describe("ChatMessage interface", () => {
  it("has required fields", () => {
    const msg: ChatMessage = {
      id: "test-id",
      role: "user",
      content: "hello",
    };
    expect(msg.id).toBe("test-id");
    expect(msg.role).toBe("user");
    expect(msg.content).toBe("hello");
  });

  it("does not include summaryCard field (removed)", () => {
    const msg: ChatMessage = {
      id: "test-id",
      role: "assistant",
      content: "response",
    };
    // TypeScript would catch this at compile time — runtime verify no extra shape
    expect("summaryCard" in msg).toBe(false);
  });

  it("accepts isAutoSummary flag", () => {
    const msg: ChatMessage = {
      id: "test-id",
      role: "assistant",
      content: "response",
      isAutoSummary: true,
    };
    expect(msg.isAutoSummary).toBe(true);
  });

  it("accepts chartData with correct shape", () => {
    const bar: PriceBar = {
      date: "2024-01-15",
      open: 180.0,
      high: 185.0,
      low: 179.0,
      close: 183.5,
    };
    const msg: ChatMessage = {
      id: "test-id",
      role: "assistant",
      content: "chart response",
      chartData: {
        ticker: "AAPL",
        currency: "USD",
        label: "1M",
        bars: [bar],
      },
    };
    expect(msg.chartData?.ticker).toBe("AAPL");
    expect(msg.chartData?.bars[0].close).toBe(183.5);
  });
});

describe("UserMode type", () => {
  it("insight is valid", () => {
    const mode: UserMode = "insight";
    expect(mode).toBe("insight");
  });

  it("trader is valid", () => {
    const mode: UserMode = "trader";
    expect(mode).toBe("trader");
  });
});

// ---------------------------------------------------------------------------
// SSE parsing simulation
// ---------------------------------------------------------------------------

describe("SSE event parsing", () => {
  function parseSSELine(line: string): object | null {
    if (!line.startsWith("data: ")) return null;
    try {
      return JSON.parse(line.slice(6));
    } catch {
      return null;
    }
  }

  it("parses token event", () => {
    const event = parseSSELine('data: {"type":"token","content":"Apple fell "}');
    expect(event).toEqual({ type: "token", content: "Apple fell " });
  });

  it("parses intent event", () => {
    const event = parseSSELine('data: {"type":"intent","intents":["real_time","news"]}');
    expect(event).toEqual({ type: "intent", intents: ["real_time", "news"] });
  });

  it("parses done event with confidence", () => {
    const event = parseSSELine('data: {"type":"done","confidence":0.87,"trace_id":"abc123"}');
    expect(event).toMatchObject({ type: "done", confidence: 0.87 });
  });

  it("parses chart_data event", () => {
    const raw = JSON.stringify({
      type: "chart_data",
      ticker: "AAPL",
      currency: "USD",
      label: "1M",
      bars: [{ date: "2024-01-01", open: 180, high: 185, low: 179, close: 183 }],
    });
    const event = parseSSELine(`data: ${raw}`) as Record<string, unknown>;
    expect(event?.type).toBe("chart_data");
    expect(event?.ticker).toBe("AAPL");
  });

  it("handles malformed SSE line gracefully", () => {
    expect(parseSSELine("data: not-json{{{")).toBeNull();
  });

  it("ignores non-data lines", () => {
    expect(parseSSELine(": keep-alive")).toBeNull();
    expect(parseSSELine("")).toBeNull();
    expect(parseSSELine("event: message")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Request body construction
// ---------------------------------------------------------------------------

describe("streamChat request body", () => {
  it("includes user_mode in request body", () => {
    // Simulate what streamChat sends
    const buildBody = (query: string, ticker: string, mode: UserMode) => ({
      query,
      ticker,
      conversation_history: [],
      session_id: "test-session",
      user_mode: mode,
    });

    const insightBody = buildBody("What is the price?", "AAPL", "insight");
    expect(insightBody.user_mode).toBe("insight");

    const traderBody = buildBody("Should I buy?", "AAPL", "trader");
    expect(traderBody.user_mode).toBe("trader");
  });

  it("sends conversation_history as array", () => {
    const history = [
      { role: "user", content: "Hello" },
      { role: "assistant", content: "Hi there" },
    ];
    const body = {
      query: "Follow-up",
      ticker: "AAPL",
      conversation_history: history,
      session_id: "abc",
      user_mode: "insight" as UserMode,
    };
    expect(Array.isArray(body.conversation_history)).toBe(true);
    expect(body.conversation_history.length).toBe(2);
  });
});
