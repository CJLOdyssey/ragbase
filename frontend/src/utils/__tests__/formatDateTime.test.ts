import { describe, it, expect } from 'vitest';
import { formatDateTime } from '../formatDateTime';

function local(iso: string): string {
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

describe('formatDateTime', { tags: ['unit'] }, () => {
  it('formats ISO to local YYYY-MM-DD HH:mm:ss', () => {
    expect(formatDateTime('2024-01-15T10:30:45Z')).toBe(local('2024-01-15T10:30:45Z'));
    expect(formatDateTime('2026-08-02T06:17:56.075619+00:00')).toBe(local('2026-08-02T06:17:56.075619+00:00'));
  });

  it('produces a well-formed datetime shape', () => {
    expect(formatDateTime('2024-01-15T10:30:45Z')).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
  });

  it('returns empty string for empty input', () => {
    expect(formatDateTime('')).toBe('');
  });

  it('returns empty string for invalid input', () => {
    expect(formatDateTime('not-a-date')).toBe('');
  });
});
