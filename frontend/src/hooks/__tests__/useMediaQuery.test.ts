import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useIsMobile, useMediaQuery } from '../useMediaQuery';

// setup.tsx 已用 defineProperty+vi.fn 定义 window.matchMedia（不可重定义），
// 这里只 mockImplementation 其返回值（matches 随测试控制）。
function mockMatches(matches: boolean) {
  const listeners = new Set<(e: { matches: boolean }) => void>();
  const mq = {
    matches,
    media: '',
    onchange: null,
    addEventListener: vi.fn(
      (_: string, cb: (e: { matches: boolean }) => void) =>
        listeners.add(cb),
    ),
    removeEventListener: vi.fn(
      (_: string, cb: (e: { matches: boolean }) => void) =>
        listeners.delete(cb),
    ),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  };
  (window.matchMedia as ReturnType<typeof vi.fn>).mockImplementation(
    () => mq,
  );
  return {
    mq,
    fireChange: (matches: boolean) => {
      mq.matches = matches;
      listeners.forEach((cb) => cb({ matches }));
    },
  };
}

describe('useMediaQuery', () => {
  beforeEach(() => {
    (window.matchMedia as ReturnType<typeof vi.fn>).mockImplementation(
      () => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }),
    );
  });

  it('returns false when the query does not match (desktop default)', () => {
    mockMatches(false);
    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'));
    expect(result.current).toBe(false);
  });

  it('returns true when the query matches', () => {
    mockMatches(true);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(true);
  });

  it('reacts to media query changes', () => {
    const { fireChange } = mockMatches(false);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);
    act(() => fireChange(true));
    expect(result.current).toBe(true);
  });

  it('cleans up the event listener on unmount', () => {
    const { mq } = mockMatches(false);
    const { unmount } = renderHook(() => useIsMobile());
    unmount();
    expect(mq.removeEventListener).toHaveBeenCalledWith(
      'change',
      expect.any(Function),
    );
  });

  it('re-subscribes when the query string changes', () => {
    const { mq } = mockMatches(false);
    const { rerender } = renderHook(
      ({ query }) => useMediaQuery(query),
      { initialProps: { query: '(max-width: 767px)' } },
    );
    expect(mq.removeEventListener).not.toHaveBeenCalled();
    rerender({ query: '(max-width: 1024px)' });
    // useEffect cleanup → removeEventListener for old query, addEventListener for new
    expect(mq.removeEventListener).toHaveBeenCalledWith(
      'change',
      expect.any(Function),
    );
  });
});
