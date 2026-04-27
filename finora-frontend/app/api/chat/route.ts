import { NextRequest } from "next/server";

// BACKEND_URL = private server-side var (HuggingFace injects, not exposed to client bundle)
// Falls back to NEXT_PUBLIC_BACKEND_URL for local dev where both are set to localhost
const BACKEND = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:7860";

export async function POST(req: NextRequest) {
  const body = await req.json();

  const upstream = await fetch(`${BACKEND}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!upstream.ok || !upstream.body) {
    return new Response(JSON.stringify({ error: "Backend unavailable" }), { status: 502 });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
