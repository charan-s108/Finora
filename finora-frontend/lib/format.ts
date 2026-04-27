export function currencySymbol(currency = "USD"): string {
  switch (currency) {
    case "INR": return "₹";
    case "GBP": return "£";
    case "EUR": return "€";
    case "JPY": return "¥";
    case "HKD": return "HK$";
    case "CAD": return "C$";
    case "AUD": return "A$";
    default: return "$";
  }
}

export function formatCurrency(value: number | null | undefined, currency = "USD"): string {
  if (value == null) return "—";
  const abs = Math.abs(value);
  if (abs >= 1e12) return `${currency === "INR" ? "₹" : "$"}${(value / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${currency === "INR" ? "₹" : "$"}${(value / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${currency === "INR" ? "₹" : "$"}${(value / 1e6).toFixed(2)}M`;
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currency === "INR" ? "INR" : "USD", maximumFractionDigits: 2 }).format(value);
}

export function formatPct(value: number | null | undefined, decimals = 2): string {
  if (value == null) return "—";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)}%`;
}

export function formatVolume(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return value.toString();
}

export function formatNumber(value: number | null | undefined, decimals = 2): string {
  if (value == null) return "—";
  return value.toFixed(decimals);
}
