export function getPctColor(pct: number): string {
  if (pct > 0) return "text-up";
  if (pct < 0) return "text-down";
  return "text-flat";
}

export function getPctSign(pct: number): string {
  if (pct > 0) return "+";
  return "";
}

export function formatPct(pct: number): string {
  return `${getPctSign(pct)}${pct.toFixed(2)}%`;
}

export function formatNumber(num: number): string {
  if (Math.abs(num) >= 1e8) return `${(num / 1e8).toFixed(2)}亿`;
  if (Math.abs(num) >= 1e4) return `${(num / 1e4).toFixed(2)}万`;
  return num.toFixed(2);
}
