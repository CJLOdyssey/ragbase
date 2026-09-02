import { STATUS_COLORS } from '../shared/statusColors';

export const LATENCY_GREEN = STATUS_COLORS.green;
export const LATENCY_AMBER = STATUS_COLORS.amber;
export const LATENCY_RED = STATUS_COLORS.red;

export function latencyColor(ms: number): string {
  if (ms < 150) return STATUS_COLORS.green;
  if (ms < 300) return STATUS_COLORS.amber;
  return STATUS_COLORS.red;
}

export function percentile(values: number[], p: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(
    sorted.length - 1,
    Math.max(0, Math.floor(p * sorted.length)),
  );
  return sorted[idx];
}
