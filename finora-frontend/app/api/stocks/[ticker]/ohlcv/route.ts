import { NextRequest } from "next/server";

export const runtime = "nodejs";

const BACKEND = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:7860";

export async function GET(
  req: NextRequest,
  { params }: { params: { ticker: string } }
) {
  const range = req.nextUrl.searchParams.get("range") || "1M";
  const url = `${BACKEND}/api/stocks/${params.ticker}/ohlcv?range=${range}`;

  try {
    const upstream = await fetch(url, { next: { revalidate: 60 } });
    if (!upstream.ok) {
      return new Response(JSON.stringify({ bars: [] }), {
        status: upstream.status,
        headers: { "Content-Type": "application/json" },
      });
    }
    const data = await upstream.json();
    return new Response(JSON.stringify(data), {
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return new Response(JSON.stringify({ bars: [] }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }
}
