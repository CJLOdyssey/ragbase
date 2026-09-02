import { useCallback, useMemo, useState } from 'react';
import type * as React from 'react';
import type { CommandOption } from '../types/input';

interface UseCommandPaletteReturn {
  open: boolean;
  query: string;
  filtered: CommandOption[];
  activeIndex: number;
  /** Call from the textarea's onKeyDown — returns true if the event was handled */
  handleKeyDown: (
    e: React.KeyboardEvent<HTMLTextAreaElement>,
    value: string,
  ) => boolean;
  /** Select a command by index — returns the replacement text（含斜杠前前缀） */
  selectCommand: (index: number, currentValue: string) => string;
  /** Set active index on mouse hover */
  setActiveIndex: (index: number) => void;
  /** Force close the palette */
  close: () => void;
  /** Call from onChange — updates query from textarea value */
  updateFromValue: (value: string) => void;
}

/**
 * Slash-command palette state machine.
 *
 * Activated when the user types '/' at the start of a line or after a space.
 * Filters commands as the user types, supports keyboard navigation,
 * and returns replacement text to be set in the textarea.
 */
export function useCommandPalette(
  commands: CommandOption[],
): UseCommandPaletteReturn {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const [slashIndex, setSlashIndex] = useState(-1); // position of '/' in the text

  const filtered = useMemo(() => {
    if (!query) return commands;
    const q = query.toLowerCase();
    return commands.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        (c.description && c.description.toLowerCase().includes(q)),
    );
  }, [commands, query]);

  const close = useCallback(() => {
    setOpen(false);
    setQuery('');
    setActiveIndex(0);
    setSlashIndex(-1);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>, value: string): boolean => {
      if (!open) {
        if (e.key === '/' && (value === '' || value.endsWith(' '))) {
          setOpen(true);
          setQuery('');
          setActiveIndex(0);
          setSlashIndex(value.length); // position where '/' was typed
          return false; // let '/' be inserted normally
        }
        return false;
      }

      // ── Palette is open ──

      if (e.key === 'Escape') {
        e.preventDefault();
        close();
        return true;
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
        return true;
      }

      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
        return true;
      }

      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        return true; // caller should call selectCommand and replace text
      }

      if (e.key === 'Backspace') {
        if (value.length <= slashIndex + 1) {
          close();
          return false; // let backspace happen normally
        }
        return false;
      }

      return false;
    },
    [open, filtered.length, close, slashIndex],
  );

  const selectCommand = useCallback(
    (index: number, currentValue: string): string => {
      if (index < 0 || index >= filtered.length) return '';
      const cmd = filtered[index];
      // 保留斜杠前的行内前缀（如「帮我 /search」选中后输出「帮我 /search 」），
      // 只替换命令段，避免整体替换 textarea 丢失前缀文本。
      const prefix = currentValue.slice(0, slashIndex);
      const replacement = `${prefix}/${cmd.name} `;
      close();
      return replacement;
    },
    [filtered, close, slashIndex],
  );

  /** Call from onChange — keeps query in sync with textarea value */
  const updateFromValue = useCallback(
    (value: string) => {
      if (!open) return;
      const q = slashIndex >= 0 ? value.slice(slashIndex + 1) : '';
      setQuery(q);
    },
    [open, slashIndex],
  );

  return {
    open,
    query,
    filtered,
    activeIndex,
    handleKeyDown,
    selectCommand,
    setActiveIndex,
    close,
    updateFromValue,
  };
}
