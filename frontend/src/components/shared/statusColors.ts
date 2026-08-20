// Centralized semantic color tokens for status / category badges.
// Replaces ad-hoc inline `rgba(...)` literals scattered across pages (DRY / 合成复用).
// Surface & text colors remain CSS variables (var(--color-*)); only SEMANTIC
// status hues are centralized here.

export const STATUS_COLORS = {
  green: '#10b981',
  red: '#ef4444',
  amber: '#f59e0b',
  blue: '#3b82f6',
  cyan: '#06b6d4',
  violet: '#8b5cf6',
  gray: '#8a8f98',
} as const;

export type StatusColorName = keyof typeof STATUS_COLORS;

/** Convert a hex color to an rgba() string with the given alpha. */
export function withAlpha(hex: string, alpha: number): string {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

const STATUS_COLOR_NAME: Record<string, StatusColorName> = {
  active: 'green',
  indexed: 'green',
  published: 'green',
  good: 'green',
  success: 'green',
  processing: 'amber',
  invited: 'amber',
  pending: 'amber',
  warn: 'amber',
  disabled: 'gray',
  inactive: 'gray',
  error: 'gray',
  failed: 'gray',
  archived: 'gray',
  draft: 'red',
  empty: 'red',
  critical: 'red',
};

/** Map a semantic state to its canonical status color. */
export function statusColor(status: string): string {
  return STATUS_COLORS[STATUS_COLOR_NAME[status] ?? 'gray'];
}
