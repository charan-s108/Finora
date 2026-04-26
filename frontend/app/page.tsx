import { TickerTape } from "@/components/ui/TickerTape";
import { Navbar } from "@/components/landing/Navbar";
import { Hero } from "@/components/landing/Hero";
import { MarketPulse } from "@/components/landing/MarketPulse";
import { Features } from "@/components/landing/Features";
import { Footer } from "@/components/landing/Footer";

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <TickerTape />
      <Navbar />

      <main className="flex-1 pt-16">
        <Hero />

        {/* Market Pulse */}
        <section className="border-t border-border py-14 px-4 bg-muted/20 dark:bg-card/20">
          <div className="max-w-7xl mx-auto">
            <div className="mb-8 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
              <div>
                <p className="text-xs font-semibold text-primary uppercase tracking-widest mb-2">
                  Live · Our Pipeline
                </p>
                <h2 className="font-heading font-bold text-3xl sm:text-4xl text-foreground mb-2">
                  Global Market Pulse
                </h2>
                <p className="text-muted-foreground text-sm">
                  30-day trends fetched from our backend · click any row to chart it · open arrow to deep-dive
                </p>
              </div>
              <span className="text-xs text-muted-foreground bg-card border border-border px-3 py-1.5 rounded-full self-start sm:self-auto shadow-sm">
                US · India · Global · 555 stocks
              </span>
            </div>
            <MarketPulse />
          </div>
        </section>

        {/* Features */}
        <Features />
      </main>

      <Footer />
    </div>
  );
}
