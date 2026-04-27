"use client";

interface Props {
  ticker: string;
  onSelect: (query: string) => void;
}

function getFollowUpChips(ticker: string): string[] {
  if (!ticker) return [
    "Why is the market down today?",
    "Top performing sectors this week",
    "Compare AAPL vs MSFT earnings",
    "Explain P/E ratio",
  ];
  return [
    `What's moving ${ticker} today?`,
    `${ticker} analyst consensus`,
    `Key risks for ${ticker}`,
    `${ticker} vs sector performance`,
  ];
}

export function SuggestionChips({ ticker, onSelect }: Props) {
  const summarizeQuery = ticker ? `Summarize ${ticker}` : "Summarize this stock";
  const chips = getFollowUpChips(ticker);

  return (
    <div className="px-3 pb-2 space-y-2">
      {/* Primary action */}
      <button
        onClick={() => onSelect(summarizeQuery)}
        className="w-full text-xs px-3 py-2 rounded-lg bg-primary/10 border border-primary/20 hover:bg-primary/20 hover:border-primary/40 transition-colors text-primary font-medium text-left"
      >
        Summarize this stock — full analysis
      </button>

      {/* Follow-up chips */}
      <div className="flex flex-wrap gap-1.5">
        {chips.map(chip => (
          <button
            key={chip}
            onClick={() => onSelect(chip)}
            className="text-[11px] px-2.5 py-1 rounded-full bg-secondary border border-border hover:border-primary/40 hover:bg-accent transition-colors text-muted-foreground hover:text-foreground"
          >
            {chip}
          </button>
        ))}
      </div>
    </div>
  );
}
