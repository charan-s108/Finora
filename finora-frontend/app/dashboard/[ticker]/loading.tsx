export default function Loading() {
  return (
    <div className="min-h-screen bg-background">
      {/* Navbar skeleton */}
      <div className="sticky top-0 z-50 border-b border-border/50 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-3">
          <div className="w-22 h-6 bg-muted rounded animate-pulse" />
          <div className="hidden sm:block w-px h-4 bg-border" />
          <div className="hidden sm:block w-12 h-4 bg-muted rounded animate-pulse" />
          <div className="flex-1" />
          <div className="w-40 h-9 bg-muted rounded-xl animate-pulse" />
          <div className="w-8 h-8 bg-muted rounded-lg animate-pulse" />
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* StockHeader skeleton */}
        <div className="rounded-xl border border-border bg-card p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-pulse">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-muted" />
            <div className="space-y-2 pt-0.5">
              <div className="flex items-center gap-2">
                <div className="w-20 h-6 bg-muted rounded" />
                <div className="w-16 h-4 bg-muted rounded" />
              </div>
              <div className="w-36 h-3.5 bg-muted rounded" />
            </div>
          </div>
          <div className="flex items-end gap-6">
            <div className="hidden sm:block w-24 h-10 bg-muted rounded" />
            <div className="space-y-1.5 text-right">
              <div className="w-28 h-8 bg-muted rounded ml-auto" />
              <div className="w-20 h-4 bg-muted rounded ml-auto" />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left column */}
          <div className="lg:col-span-2 space-y-4">
            {/* PriceChart skeleton */}
            <div className="rounded-xl border border-border bg-card overflow-hidden animate-pulse">
              <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-muted" />
                <div className="w-24 h-4 bg-muted rounded" />
                <div className="ml-auto flex gap-1.5">
                  {Array.from({ length: 7 }).map((_, i) => (
                    <div key={i} className="w-8 h-6 bg-muted rounded-md" />
                  ))}
                </div>
              </div>
              <div className="p-4 h-72 bg-muted/20" />
            </div>

            {/* FundamentalsGrid skeleton */}
            <div className="rounded-xl border border-border bg-card overflow-hidden animate-pulse">
              <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-muted" />
                <div className="w-28 h-4 bg-muted rounded" />
              </div>
              <div className="p-3 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="rounded-xl border border-border p-3.5 space-y-2">
                    <div className="w-16 h-2.5 bg-muted rounded" />
                    <div className="w-20 h-5 bg-muted rounded" />
                  </div>
                ))}
              </div>
            </div>

            {/* NewsRagPanel skeleton */}
            <div className="rounded-xl border border-border bg-card overflow-hidden animate-pulse">
              <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-muted" />
                <div className="w-20 h-4 bg-muted rounded" />
                <div className="ml-auto w-16 h-5 bg-muted rounded-full" />
              </div>
              <div className="divide-y divide-border">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="px-4 py-3 space-y-1.5">
                    <div className="h-3.5 bg-muted rounded w-full" />
                    <div className="h-3 bg-muted rounded w-4/5" />
                    <div className="flex gap-2 pt-0.5">
                      <div className="w-12 h-3 bg-muted rounded-full" />
                      <div className="w-16 h-3 bg-muted rounded" />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* HistoricalRagPanel skeleton */}
            <div className="rounded-xl border border-border bg-card overflow-hidden animate-pulse">
              <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-muted" />
                <div className="w-36 h-4 bg-muted rounded" />
                <div className="ml-auto w-16 h-5 bg-muted rounded-full" />
              </div>
              <div className="divide-y divide-border">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="px-4 py-3 space-y-1.5">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-3 bg-muted rounded-full" />
                      <div className="w-24 h-3 bg-muted rounded" />
                    </div>
                    <div className="h-3 bg-muted rounded w-full" />
                    <div className="h-3 bg-muted rounded w-2/3" />
                  </div>
                ))}
              </div>
            </div>

            {/* SimilarStocks skeleton — mobile only */}
            <div className="lg:hidden rounded-xl border border-border bg-card overflow-hidden animate-pulse">
              <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-muted" />
                <div className="w-28 h-4 bg-muted rounded" />
                <div className="ml-auto w-14 h-5 bg-muted rounded-full" />
              </div>
              <div className="divide-y divide-border">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="px-4 py-3 flex items-center gap-3">
                    <div className="w-14 h-9 rounded-lg bg-muted flex-shrink-0" />
                    <div className="flex-1 space-y-1.5">
                      <div className="h-3 bg-muted rounded w-3/4" />
                      <div className="flex gap-1.5">
                        <div className="w-14 h-3 bg-muted rounded" />
                        <div className="w-20 h-3 bg-muted rounded" />
                      </div>
                    </div>
                    <div className="w-3.5 h-3.5 bg-muted rounded" />
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right sidebar */}
          <div className="hidden lg:block space-y-4">
            {/* AnalystConsensus skeleton */}
            <div className="rounded-xl border border-border bg-card p-4 space-y-3 animate-pulse">
              <div className="flex items-center justify-between">
                <div className="w-36 h-4 bg-muted rounded" />
                <div className="w-16 h-4 bg-muted rounded" />
              </div>
              <div className="h-2 bg-muted rounded-full" />
              <div className="flex justify-between">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-muted" />
                    <div className="w-10 h-3 bg-muted rounded" />
                  </div>
                ))}
              </div>
              <div className="border-t border-border pt-2 flex justify-between">
                <div className="w-24 h-3 bg-muted rounded" />
                <div className="w-16 h-4 bg-muted rounded" />
              </div>
            </div>

            {/* StockAbout skeleton */}
            <div className="rounded-xl border border-border bg-card overflow-hidden animate-pulse">
              <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-muted" />
                <div className="w-20 h-4 bg-muted rounded" />
              </div>
              <div className="p-4 space-y-2">
                <div className="h-3 bg-muted rounded w-full" />
                <div className="h-3 bg-muted rounded w-full" />
                <div className="h-3 bg-muted rounded w-4/5" />
                <div className="h-3 bg-muted rounded w-2/3" />
                <div className="h-3 bg-muted rounded w-3/4" />
              </div>
              <div className="px-4 pb-4 grid grid-cols-2 gap-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="rounded-lg bg-muted/40 p-2 space-y-1">
                    <div className="w-12 h-2.5 bg-muted rounded" />
                    <div className="w-16 h-3 bg-muted rounded" />
                  </div>
                ))}
              </div>
            </div>

            {/* SimilarStocks skeleton */}
            <div className="rounded-xl border border-border bg-card overflow-hidden animate-pulse">
              <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-muted" />
                <div className="w-28 h-4 bg-muted rounded" />
                <div className="ml-auto w-14 h-5 bg-muted rounded-full" />
              </div>
              <div className="divide-y divide-border">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="px-4 py-3 flex items-center gap-3">
                    <div className="w-14 h-9 rounded-lg bg-muted flex-shrink-0" />
                    <div className="flex-1 space-y-1.5">
                      <div className="h-3 bg-muted rounded w-3/4" />
                      <div className="flex gap-1.5">
                        <div className="w-14 h-3 bg-muted rounded" />
                        <div className="w-20 h-3 bg-muted rounded" />
                      </div>
                    </div>
                    <div className="w-3.5 h-3.5 bg-muted rounded" />
                  </div>
                ))}
              </div>
              <div className="px-4 py-2 border-t border-border/50 bg-muted/10">
                <div className="w-32 h-2.5 bg-muted rounded mx-auto" />
              </div>
            </div>

            {/* SectorHeatmap skeleton */}
            <div className="rounded-xl border border-border bg-card overflow-hidden animate-pulse">
              <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-muted" />
                <div className="w-36 h-4 bg-muted rounded" />
                <div className="ml-auto w-10 h-5 bg-muted rounded-full" />
              </div>
              <div className="px-4 py-2 border-b border-border/50 flex gap-4">
                <div className="w-28 h-3 bg-muted rounded" />
                <div className="w-24 h-3 bg-muted rounded" />
              </div>
              <div className="p-3 grid grid-cols-3 gap-1.5">
                {Array.from({ length: 12 }).map((_, i) => (
                  <div key={i} className="rounded-lg bg-muted/40 p-2.5 space-y-1">
                    <div className="h-2.5 bg-muted rounded w-3/4" />
                    <div className="h-2 bg-muted rounded w-1/2" />
                    <div className="h-3.5 bg-muted rounded w-2/3 mt-0.5" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
