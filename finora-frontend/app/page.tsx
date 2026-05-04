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
        <section className="border-t border-border py-16 px-4">
          <div className="max-w-7xl mx-auto">
            <div className="mb-10 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
              <div>
                <p className="text-xs font-bold text-primary uppercase tracking-[0.2em] mb-2">
                  Live · Our Pipeline
                </p>
                <h2 className="font-heading font-black text-3xl sm:text-4xl text-foreground mb-2 tracking-tight">
                  Global Market Pulse
                </h2>
                <p className="text-muted-foreground text-sm max-w-md">
                  30-day trends — click any row to chart it · open arrow to deep-dive the full dashboard
                </p>
              </div>
              <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground bg-card border border-border px-3 py-1.5 rounded-full self-start sm:self-auto shadow-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                US · India · Global · 555 stocks
              </span>
            </div>
            <MarketPulse />
          </div>
        </section>

        {/* Stats + Features */}
        <Features />
      </main>

      <Footer />
    </div>
  );
}
