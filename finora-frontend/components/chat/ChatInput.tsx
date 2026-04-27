"use client";

import { Send } from "lucide-react";
import { useRef } from "react";
import type { UserMode } from "@/lib/streaming";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  userMode: UserMode;
  onModeChange: (mode: UserMode) => void;
}

export function ChatInput({ value, onChange, onSubmit, disabled, userMode, onModeChange }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) onSubmit();
    }
  };

  return (
    <div className="border-t border-border">
      {/* Mode toggle */}
      <div className="flex items-center gap-1.5 px-3 pt-2 pb-0">
        <span className="text-[10px] text-muted-foreground mr-0.5">Mode:</span>
        <button
          onClick={() => onModeChange("insight")}
          className={`text-[10px] px-2.5 py-1 rounded-full font-medium transition-colors border ${
            userMode === "insight"
              ? "bg-primary text-primary-foreground border-primary"
              : "bg-transparent text-muted-foreground border-border hover:border-primary/40 hover:text-foreground"
          }`}
        >
          Insight
        </button>
        <button
          onClick={() => onModeChange("trader")}
          className={`text-[10px] px-2.5 py-1 rounded-full font-medium transition-colors border ${
            userMode === "trader"
              ? "bg-orange-500 text-white border-orange-500"
              : "bg-transparent text-muted-foreground border-border hover:border-orange-400/40 hover:text-foreground"
          }`}
        >
          Trader
        </button>
        <span className="text-[9px] text-muted-foreground/50 ml-1">
          {userMode === "trader" ? "Signals & momentum · Risk awareness required" : "Analysis & fundamentals · No buy/sell signals"}
        </span>
      </div>

      {/* Input row */}
      <div className="px-3 py-2.5 flex items-end gap-2">
        <textarea
          ref={textareaRef}
          className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none resize-none max-h-24 leading-relaxed"
          placeholder={
            userMode === "trader"
              ? "Ask about signals, momentum, key levels..."
              : "Ask about earnings, fundamentals, sector trends..."
          }
          value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={disabled}
        />
        <button
          onClick={onSubmit}
          disabled={!value.trim() || disabled}
          className={`w-8 h-8 flex items-center justify-center rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0 ${
            userMode === "trader"
              ? "bg-orange-500 hover:bg-orange-400"
              : "bg-primary hover:bg-primary/90"
          }`}
        >
          <Send className="w-3.5 h-3.5 text-white" />
        </button>
      </div>
    </div>
  );
}
