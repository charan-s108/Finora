export default function Loading() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header skeleton */}
      <div className="sticky top-0 z-30 border-b border-border bg-background/95 backdrop-blur-sm px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-24 h-5 bg-muted rounded animate-pulse" />
            <div className="w-16 h-5 bg-muted rounded animate-pulse" />
          </div>
          <div className="w-48 h-9 bg-muted rounded-xl animate-pulse" />
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Stock header skeleton */}
        <div className="mb-6 flex items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="w-32 h-7 bg-muted rounded animate-pulse" />
            <div className="w-48 h-4 bg-muted rounded animate-pulse" />
          </div>
          <div className="text-right space-y-2">
            <div className="w-28 h-8 bg-muted rounded animate-pulse ml-auto" />
            <div className="w-20 h-4 bg-muted rounded animate-pulse ml-auto" />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Price chart skeleton */}
            <div className="rounded-xl border border-border bg-card p-4 h-72 animate-pulse">
              <div className="w-40 h-5 bg-muted rounded mb-4" />
              <div className="h-52 bg-muted/50 rounded-lg" />
            </div>

            {/* Fundamentals grid skeleton */}
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="w-32 h-5 bg-muted rounded mb-4 animate-pulse" />
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="rounded-lg border border-border p-3 space-y-2 animate-pulse">
                    <div className="w-14 h-3 bg-muted rounded" />
                    <div className="w-20 h-5 bg-muted rounded" />
                  </div>
                ))}
              </div>
            </div>

            {/* News skeleton */}
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="w-28 h-5 bg-muted rounded mb-4 animate-pulse" />
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="flex gap-3 animate-pulse">
                    <div className="w-16 h-4 bg-muted rounded flex-shrink-0" />
                    <div className="flex-1 space-y-1.5">
                      <div className="h-3 bg-muted rounded w-full" />
                      <div className="h-3 bg-muted rounded w-3/4" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right column */}
          <div className="space-y-6">
            {/* Analyst consensus skeleton */}
            <div className="rounded-xl border border-border bg-card p-4 animate-pulse">
              <div className="w-36 h-5 bg-muted rounded mb-4" />
              <div className="h-8 bg-muted rounded-full mb-3" />
              <div className="grid grid-cols-3 gap-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="h-12 bg-muted rounded-lg" />
                ))}
              </div>
            </div>

            {/* About skeleton */}
            <div className="rounded-xl border border-border bg-card p-4 animate-pulse">
              <div className="w-20 h-5 bg-muted rounded mb-4" />
              <div className="space-y-2">
                <div className="h-3 bg-muted rounded w-full" />
                <div className="h-3 bg-muted rounded w-full" />
                <div className="h-3 bg-muted rounded w-4/5" />
                <div className="h-3 bg-muted rounded w-2/3" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
