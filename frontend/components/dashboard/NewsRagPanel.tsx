import { ExternalLink, Newspaper, TrendingUp, TrendingDown, Minus } from "lucide-react";

interface NewsItem {
  text?: string;
  title?: string;
  source?: string;
  published_at?: string;
  url?: string;
  sentiment_score?: number;
}

interface Props {
  items: NewsItem[];
}

function SentimentBadge({ score }: { score?: number }) {
  if (score == null) return null;
  if (score > 0.3)
    return (
      <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 px-1.5 py-0.5 rounded-full border border-emerald-500/20">
        <TrendingUp className="w-2.5 h-2.5" /> Bullish
      </span>
    );
  if (score < -0.3)
    return (
      <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold bg-rose-500/15 text-rose-400 px-1.5 py-0.5 rounded-full border border-rose-500/20">
        <TrendingDown className="w-2.5 h-2.5" /> Bearish
      </span>
    );
  return (
    <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold bg-muted text-muted-foreground px-1.5 py-0.5 rounded-full border border-border">
      <Minus className="w-2.5 h-2.5" /> Neutral
    </span>
  );
}

function formatDate(raw?: string) {
  if (!raw) return null;
  try {
    return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(new Date(raw));
  } catch {
    return raw;
  }
}

export function NewsRagPanel({ items }: Props) {
  const displayed = items.slice(0, 6);

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-muted/30">
        <div className="w-6 h-6 rounded-md bg-primary/10 flex items-center justify-center">
          <Newspaper className="w-3.5 h-3.5 text-primary" />
        </div>
        <h3 className="text-sm font-semibold text-foreground">News RAG</h3>
        <span className="ml-auto text-[10px] font-medium bg-primary/10 text-primary px-2 py-0.5 rounded-full border border-primary/20">
          {displayed.length} sources
        </span>
      </div>

      {displayed.length === 0 ? (
        <div className="px-4 py-8 text-center">
          <Newspaper className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
          <p className="text-xs text-muted-foreground">No news ingested yet</p>
        </div>
      ) : (
        <ul className="divide-y divide-border">
          {displayed.map((item, i) => (
            <li key={i} className="px-4 py-3 hover:bg-muted/20 transition-colors group">
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <p className="text-xs font-medium text-foreground leading-relaxed flex-1">
                  {item.title || item.text?.slice(0, 140)}
                </p>
                {item.url && (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-shrink-0 p-1 rounded-md hover:bg-primary/10 text-muted-foreground hover:text-primary transition-colors opacity-0 group-hover:opacity-100"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <SentimentBadge score={item.sentiment_score} />
                {item.source && (
                  <span className="text-[10px] text-muted-foreground font-medium">{item.source}</span>
                )}
                {item.published_at && (
                  <span className="text-[10px] text-muted-foreground/60">· {formatDate(item.published_at)}</span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
