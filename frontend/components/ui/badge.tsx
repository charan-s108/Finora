import { cn } from "@/lib/utils";

interface Props {
  children: React.ReactNode;
  variant?: "default" | "positive" | "negative" | "neutral";
  className?: string;
}

export function Badge({ children, variant = "default", className }: Props) {
  const variants = {
    default: "bg-secondary text-foreground border-border",
    positive: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
    negative: "bg-rose-500/15 text-rose-400 border-rose-500/20",
    neutral: "bg-yellow-500/15 text-yellow-400 border-yellow-500/20",
  };
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border", variants[variant], className)}>
      {children}
    </span>
  );
}
