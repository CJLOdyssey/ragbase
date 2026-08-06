import { useAutoSave } from '../useAutoSave';
import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

let mockAutoSave = true;

vi.mock('../../contexts/SettingsContext', () => ({
  useSettings: () => ({
    settings: { autoSave: mockAutoSave },
    updateSettings: vi.fn(),
  }),
}));

describe('useAutoSave', { tags: ['unit'] }, () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockAutoSave = true;
    localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('writes data to localStorage after 2s', () => {
    renderHook(() => useAutoSave('draft', { text: 'hi' }));
    expect(localStorage.getItem('draft')).toBeNull();
    vi.advanceTimersByTime(2000);
    expect(localStorage.getItem('draft')).toBe('{"text":"hi"}');
  });

  it('skips saving when autoSave disabled', () => {
    mockAutoSave = false;
    renderHook(() => useAutoSave('draft', { text: 'hi' }));
    vi.advanceTimersByTime(2000);
    expect(localStorage.getItem('draft')).toBeNull();
  });

  it('skips saving when enabled flag is false', () => {
    renderHook(() => useAutoSave('draft', { text: 'hi' }, false));
    vi.advanceTimersByTime(2000);
    expect(localStorage.getItem('draft')).toBeNull();
  });

  it('survives localStorage quota errors', () => {
    const setItem = vi.fn(() => {
      throw new Error('QuotaExceeded');
    });
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(),
      setItem,
      clear: vi.fn(),
      removeItem: vi.fn(),
    });
    renderHook(() => useAutoSave('draft', { text: 'hi' }));
    vi.advanceTimersByTime(2000);
    expect(setItem).toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it('resets the timer when data changes', () => {
    const { rerender } = renderHook(({ data }) => useAutoSave('draft', data), {
      initialProps: { data: { v: 1 } },
    });
    vi.advanceTimersByTime(1000);
    rerender({ data: { v: 2 } });
    vi.advanceTimersByTime(1000);
    expect(localStorage.getItem('draft')).toBeNull();
    vi.advanceTimersByTime(1000);
    expect(localStorage.getItem('draft')).toBe('{"v":2}');
  });
});
