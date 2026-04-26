"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Search, ArrowLeft } from "lucide-react";
import { FinoraIcon } from "@/components/ui/FinoraIcon";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const router = useRouter();

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4">
      <div className="flex flex-col items-center text-center max-w-md gap-6">
        {/* Icon */}
        <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
          <FinoraIcon size={32} className="text-primary" />
        </div>

        {/* Error badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-rose-500/10 border border-rose-500/20">
          <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
          <span className="text-xs font-medium text-rose-400">Stock not found</span>
        </div>

        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-foreground">Ticker not in universe</h1>
          <p className="text-muted-foreground text-sm leading-relaxed">
            This ticker isn&apos;t in the Finora universe of 555+ US &amp; Indian stocks.
            Try searching for a valid ticker below.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 w-full">
          <button
            onClick={() => router.push("/")}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-border bg-card hover:bg-secondary transition-colors text-sm font-medium text-foreground"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </button>
          <button
            onClick={() => router.push("/?search=1")}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary hover:bg-primary/90 transition-colors text-sm font-medium text-primary-foreground"
          >
            <Search className="w-4 h-4" />
            Search Stocks
          </button>
        </div>

        <button
          onClick={reset}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors underline underline-offset-4"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
