import { notFound } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { getStockDetail } from "@/lib/api";
import { TickerTape } from "@/components/ui/TickerTape";
import { StockHeader } from "@/components/dashboard/StockHeader";
import { FundamentalsGrid } from "@/components/dashboard/FundamentalsGrid";
import { PriceChart } from "@/components/dashboard/PriceChart";
import { NewsRagPanel } from "@/components/dashboard/NewsRagPanel";
import { HistoricalRagPanel } from "@/components/dashboard/HistoricalRagPanel";
import { AnalystConsensus } from "@/components/dashboard/AnalystConsensus";
import { StockAbout } from "@/components/dashboard/StockAbout";
import { StockSearch } from "@/components/dashboard/StockSearch";
import { ChatWidget } from "@/components/chat/ChatWidget";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

interface Props {
  params: { ticker: string };
}

export async function generateMetadata({ params }: Props) {
  const ticker = decodeURIComponent(params.ticker).toUpperCase();
  return {
    title: `${ticker} — Finora AI Stock Analysis`,
    description: `Real-time AI analysis for ${ticker}. Price, fundamentals, technicals and news.`,
  };
}

export default async function TickerPage({ params }: Props) {
  const ticker = decodeURIComponent(params.ticker).toUpperCase();
  const stock = await getStockDetail(ticker);

  if (!stock) notFound();

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <TickerTape />

      {/* Navbar */}
      <header className="sticky top-0 z-50 border-b border-border/50 bg-transparent backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity flex-shrink-0">
            <Image
              src="/finora_logo.png"
              alt="Finora"
              width={88}
              height={24}
              className="h-6 w-auto"
            />
          </Link>

          <span className="text-border hidden sm:block">|</span>
          <span className="font-mono font-bold text-sm text-foreground hidden sm:block">{ticker}</span>

          <div className="flex-1" />

          <StockSearch compact />
          <ThemeToggle />
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6 space-y-6">
        {/* Price header + sparkline */}
        <StockHeader stock={stock} />

        {/* Main grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left: main content */}
          <div className="lg:col-span-2 space-y-4">
            <PriceChart ticker={ticker} currency={stock.currency} />
            <div className="lg:hidden">
              <AnalystConsensus consensus={stock.analyst_consensus ?? null} />
            </div>
            <div className="lg:hidden">
              <StockAbout stock={stock} />
            </div>
            <FundamentalsGrid stock={stock} />
            <NewsRagPanel items={stock.news_rag ?? []} />
            <HistoricalRagPanel signals={stock.historical_signals ?? []} />
          </div>

          {/* Right: desktop sidebar */}
          <div className="hidden lg:block space-y-4">
            <AnalystConsensus consensus={stock.analyst_consensus ?? null} />
            <StockAbout stock={stock} />
          </div>
        </div>
      </main>

      <ChatWidget ticker={ticker} />
    </div>
  );
}