import type * as React from 'react';
import { useMessageComposer } from '../useMessageComposer';
import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

function keyEvent(
  partial: Partial<React.KeyboardEvent<HTMLTextAreaElement>>,
): React.KeyboardEvent<HTMLTextAreaElement> {
  return {
    key: 'Enter',
    shiftKey: false,
    ctrlKey: false,
    metaKey: false,
    preventDefault: vi.fn(),
    nativeEvent: { isComposing: false },
    ...partial,
  } as unknown as React.KeyboardEvent<HTMLTextAreaElement>;
}

describe('useMessageComposer', { tags: ['unit'] }, () => {
  it('submits sanitized text and clears value', () => {
    const onSend = vi.fn();
    const { result } = renderHook(() => useMessageComposer({ onSend }));
    act(() => result.current.setValue('  hello  '));
    let ok = false;
    act(() => {
      ok = result.current.submit();
    });
    expect(ok).toBe(true);
    expect(onSend).toHaveBeenCalledWith('hello');
    expect(result.current.value).toBe('');
  });

  it('rejects whitespace-only input and clears it', () => {
    const onSend = vi.fn();
    const { result } = renderHook(() => useMessageComposer({ onSend }));
    act(() => result.current.setValue('   '));
    let ok = true;
    act(() => {
      ok = result.current.submit();
    });
    expect(ok).toBe(false);
    expect(onSend).not.toHaveBeenCalled();
    expect(result.current.value).toBe('');
  });

  it('Enter sends in enter mode', () => {
    const onSend = vi.fn();
    const { result } = renderHook(() =>
      useMessageComposer({ onSend, sendMode: 'enter' }),
    );
    act(() => result.current.setValue('hi'));
    act(() => result.current.handleKeyDown(keyEvent({ shiftKey: false })));
    expect(onSend).toHaveBeenCalledWith('hi');
  });

  it('Shift+Enter inserts newline instead of sending', () => {
    const onSend = vi.fn();
    const { result } = renderHook(() =>
      useMessageComposer({ onSend, sendMode: 'enter' }),
    );
    act(() => result.current.setValue('hi'));
    act(() => result.current.handleKeyDown(keyEvent({ shiftKey: true })));
    expect(onSend).not.toHaveBeenCalled();
  });

  it('Ctrl+Enter sends in ctrl-enter mode, plain Enter does not', () => {
    const onSend = vi.fn();
    const { result } = renderHook(() =>
      useMessageComposer({ onSend, sendMode: 'ctrl-enter' }),
    );
    act(() => result.current.setValue('hi'));
    act(() => result.current.handleKeyDown(keyEvent({ ctrlKey: true })));
    expect(onSend).toHaveBeenCalledTimes(1);
    act(() => result.current.handleKeyDown(keyEvent({ ctrlKey: false })));
    expect(onSend).toHaveBeenCalledTimes(1);
  });

  it('ignores Enter during IME composition', () => {
    const onSend = vi.fn();
    const { result } = renderHook(() => useMessageComposer({ onSend }));
    act(() => result.current.setValue('hi'));
    act(() =>
      result.current.handleKeyDown(
        keyEvent({ nativeEvent: { isComposing: true } }),
      ),
    );
    expect(onSend).not.toHaveBeenCalled();
  });

  it('reports hasContent and charCount', () => {
    const { result } = renderHook(() =>
      useMessageComposer({ onSend: vi.fn(), maxLength: 50 }),
    );
    expect(result.current.hasContent).toBe(false);
    expect(result.current.charCount).toBe(0);
    expect(result.current.maxLength).toBe(50);
    act(() => result.current.setValue('abc'));
    expect(result.current.hasContent).toBe(true);
    expect(result.current.charCount).toBe(3);
  });
});
