import { describe, it, expect, vi, afterEach } from 'vitest';
import { uid } from '../uid';

describe('uid', { tags: ['unit'] }, () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns a string', () => {
    expect(typeof uid()).toBe('string');
  });

  it('returns non-empty string', () => {
    expect(uid().length).toBeGreaterThan(0);
  });

  it('returns different values on successive calls', () => {
    const a = uid();
    const b = uid();
    expect(a).not.toBe(b);
  });

  it('includes timestamp component', () => {
    const now = Date.now();
    vi.setSystemTime(now);
    const id = uid();
    expect(id.startsWith(now.toString(36))).toBe(true);
  });
});
