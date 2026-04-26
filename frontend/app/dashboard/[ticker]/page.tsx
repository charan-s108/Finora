import { notFound } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { getStockDetail, getSectors } from "@/lib/api";
import { TickerTape } from "@/components/ui/TickerTape";
import { StockHeader } from "@/components/dashboard/StockHeader";
import { FundamentalsGrid } from "@/components/dashboard/FundamentalsGrid";
import { PriceChart } from "@/components/dashboard/PriceChart";
import { NewsRagPanel } from "@/components/dashboard/NewsRagPanel";
import { HistoricalRagPanel } from "@/components/dashboard/HistoricalRagPanel";
import { AnalystConsensus } from "@/components/dashboard/AnalystConsensus";
import { StockAbout } from "@/components/dashboard/StockAbout";
import { SectorHeatmap } from "@/components/dashboard/SectorHeatmap";
import { SimilarStocks } from "@/components/dashboard/SimilarStocks";
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
  const [stock, sectors] = await Promise.all([
    getStockDetail(ticker),
    getSectors(),
  ]);

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
            {/* Mobile only — similar stocks below historical */}
            <div className="lg:hidden">
              <SimilarStocks stocks={stock.similar_stocks ?? []} currentTicker={ticker} />
            </div>
          </div>

          {/* Right: desktop sidebar */}
          <div className="hidden lg:block space-y-4">
            <AnalystConsensus consensus={stock.analyst_consensus ?? null} />
            <StockAbout stock={stock} />
            <SimilarStocks stocks={stock.similar_stocks ?? []} currentTicker={ticker} />
            <SectorHeatmap data={sectors} />
          </div>
        </div>
      </main>

      <ChatWidget ticker={ticker} />

      {/* Footer */}
      <footer className="border-t border-border/40 bg-background/60 backdrop-blur-sm mt-2">
        <div className="max-w-7xl mx-auto px-4 h-10 flex items-center justify-between gap-4">
          <p className="text-[11px] text-muted-foreground/50">
            © {new Date().getFullYear()} Finora · For informational purposes only · Not financial advice
          </p>
          <Link href="/eval" className="text-[11px] text-muted-foreground/40 hover:text-muted-foreground transition-colors flex-shrink-0">
            RAG Eval →
          </Link>
        </div>
      </footer>
    </div>
  );
}