export function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(1)}%`;
}

export function formatMs(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return `${value}ms`;
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat().format(value);
}

export function formatAlertValue(code: string, value: number): string {
  if (code === 'good_ratio_low') return formatPct(value);
  if (code === 'empty_recall_high') return `${value.toFixed(1)}%`;
  return formatMs(Math.round(value));
}
