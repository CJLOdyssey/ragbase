import { useState, useCallback, useRef } from 'react';
import { validateInput } from '../utils/validation';
import type * as React from 'react';

interface UseMessageComposerOptions {
  /** External submit handler — receives sanitized text */
  onSend: (text: string) => void;
  /** Max characters allowed */
  maxLength?: number;
  /** Send mode: 'enter' = Enter sends, 'ctrl-enter' = Ctrl+Enter sends */
  sendMode?: 'enter' | 'ctrl-enter';
}

interface UseMessageComposerReturn {
  value: string;
  setValue: (v: string) => void;
  /** Deferred value for filtering/search (avoids stutter on fast typing) */
  submit: () => boolean;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  /** True when the input contains non-whitespace content */
  hasContent: boolean;
  charCount: number;
  maxLength: number;
}

/**
 * Self-contained message input state machine.
 *
 * All input state lives here — no parent re-render on every keystroke.
 * Uses a ref to always read the latest value in callbacks without stale closures.
 */
export function useMessageComposer({ onSend, maxLength = 10000, sendMode = 'enter' }: UseMessageComposerOptions): UseMessageComposerReturn {
  const [value, setValue] = useState('');
  const valueRef = useRef(value);
  // Keep ref in sync during render — intentional, avoids stale closures in callbacks
  valueRef.current = value; // eslint-disable-line react-hooks/refs

  const hasContent = value.trim().length > 0;
  const charCount = value.length;

  const submit = useCallback((): boolean => {
    const text = valueRef.current;
    const { valid, sanitized } = validateInput(text);
    if (!valid) {
      // Always clear whitespace-only input to avoid noise on accidental Enter
      if (!text.trim()) setValue('');
      return false;
    }
    setValue('');
    onSend(sanitized);
    return true;
  }, [onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Ignore IME composition events — pressing Enter to confirm a
      // candidate character (Chinese/Japanese/Korean) must not send.
      if (e.nativeEvent.isComposing) return;

      if (sendMode === 'enter') {
        // Enter sends, Shift+Enter inserts newline
        if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
          e.preventDefault();
          submit();
        }
      } else {
        // Ctrl+Enter sends, Enter inserts newline
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && !e.shiftKey) {
          e.preventDefault();
          submit();
        }
      }
    },
    [submit, sendMode],
  );

  return { value, setValue, submit, handleKeyDown, hasContent, charCount, maxLength };
}
