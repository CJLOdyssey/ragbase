import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useCopyToClipboard } from '../useCopyToClipboard';

describe('useCopyToClipboard', { tags: ['unit'] }, () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('copies via navigator.clipboard and reports isCopied', async () => {
    vi.useFakeTimers();
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('navigator', { clipboard: { writeText } });
    const { result } = renderHook(() => useCopyToClipboard());
    let ok = false;
    await act(async () => { ok = await result.current.copy('text', 'k1'); });
    expect(ok).toBe(true);
    expect(writeText).toHaveBeenCalledWith('text');
    expect(result.current.isCopied('k1')).toBe(true);
    await act(async () => { vi.advanceTimersByTime(1000); });
    expect(result.current.isCopied('k1')).toBe(false);
  });

  it('falls back to execCommand when clipboard API missing', async () => {
    vi.stubGlobal('navigator', {});
    Object.defineProperty(document, 'execCommand', { value: vi.fn(() => true), configurable: true, writable: true });
    const { result } = renderHook(() => useCopyToClipboard());
    let ok = false;
    await act(async () => { ok = await result.current.copy('fallback'); });
    expect(ok).toBe(true);
    expect(document.execCommand).toHaveBeenCalledWith('copy');
    expect(result.current.isCopied()).toBe(true);
  });

  it('returns false and clears copied state on failure', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('denied'));
    vi.stubGlobal('navigator', { clipboard: { writeText } });
    const { result } = renderHook(() => useCopyToClipboard());
    let ok = true;
    await act(async () => { ok = await result.current.copy('text'); });
    expect(ok).toBe(false);
    expect(result.current.isCopied()).toBe(false);
  });

  it('uses default key when none provided', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('navigator', { clipboard: { writeText } });
    const { result } = renderHook(() => useCopyToClipboard());
    await act(async () => { await result.current.copy('a'); });
    await act(async () => { await result.current.copy('b'); });
    expect(result.current.isCopied()).toBe(true);
  });
});
