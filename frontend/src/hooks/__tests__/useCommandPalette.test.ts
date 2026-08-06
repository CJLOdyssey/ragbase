import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useCommandPalette } from '../useCommandPalette';
import type { CommandOption } from '../../types/input';
import type * as React from 'react';

const commands: CommandOption[] = [
  { id: 'c1', name: 'xhs', description: '小红书笔记' },
  { id: 'c2', name: 'gzh', source: 'agent' },
];

function keyEvent(key: string, extra: Partial<React.KeyboardEvent<HTMLTextAreaElement>> = {}): React.KeyboardEvent<HTMLTextAreaElement> {
  return {
    key,
    shiftKey: false,
    preventDefault: vi.fn(),
    ...extra,
  } as unknown as React.KeyboardEvent<HTMLTextAreaElement>;
}

describe('useCommandPalette', { tags: ['unit'] }, () => {
  beforeEach(() => vi.clearAllMocks());

  it('opens when / typed at start of value', () => {
    const { result } = renderHook(() => useCommandPalette(commands));
    act(() => {
      const handled = result.current.handleKeyDown(keyEvent('/'), '');
      expect(handled).toBe(false);
    });
    expect(result.current.open).toBe(true);
    expect(result.current.query).toBe('');
  });

  it('opens when / typed after a space, not mid-word', () => {
    const { result } = renderHook(() => useCommandPalette(commands));
    act(() => result.current.handleKeyDown(keyEvent('/'), 'hello '));
    expect(result.current.open).toBe(true);
    act(() => result.current.setActiveIndex(0));
    act(() => {
      result.current.handleKeyDown(keyEvent('/'), 'hello');
    });
    expect(result.current.open).toBe(true);
  });

  it('filters commands by query case-insensitively', () => {
    const { result } = renderHook(() => useCommandPalette(commands));
    act(() => result.current.handleKeyDown(keyEvent('/'), ''));
    act(() => result.current.updateFromValue('/XHS'));
    expect(result.current.query).toBe('XHS');
    expect(result.current.filtered.map((c) => c.id)).toEqual(['c1']);
  });

  it('shows all commands when query is empty', () => {
    const { result } = renderHook(() => useCommandPalette(commands));
    expect(result.current.filtered).toHaveLength(2);
  });

  it('navigates with ArrowDown/ArrowUp clamped to bounds', () => {
    const { result } = renderHook(() => useCommandPalette(commands));
    act(() => result.current.handleKeyDown(keyEvent('/'), ''));
    act(() => result.current.handleKeyDown(keyEvent('ArrowDown')));
    expect(result.current.activeIndex).toBe(1);
    act(() => result.current.handleKeyDown(keyEvent('ArrowDown')));
    expect(result.current.activeIndex).toBe(1);
    act(() => result.current.handleKeyDown(keyEvent('ArrowUp')));
    expect(result.current.activeIndex).toBe(0);
    act(() => result.current.handleKeyDown(keyEvent('ArrowUp')));
    expect(result.current.activeIndex).toBe(0);
  });

  it('handles Escape to close and Enter without selecting', () => {
    const { result } = renderHook(() => useCommandPalette(commands));
    act(() => result.current.handleKeyDown(keyEvent('/'), ''));
    let handledEscape = false;
    act(() => { handledEscape = result.current.handleKeyDown(keyEvent('Escape')); });
    expect(handledEscape).toBe(true);
    expect(result.current.open).toBe(false);
    act(() => result.current.handleKeyDown(keyEvent('/'), ''));
    act(() => result.current.handleKeyDown(keyEvent('Enter')));
    expect(result.current.open).toBe(true);
  });

  it('closes when backspacing past the slash', () => {
    const { result } = renderHook(() => useCommandPalette(commands));
    act(() => result.current.handleKeyDown(keyEvent('/'), ''));
    let handled = true;
    act(() => { handled = result.current.handleKeyDown(keyEvent('Backspace'), '/'); });
    expect(handled).toBe(false);
    expect(result.current.open).toBe(false);
  });

  it('keeps palette open on backspace after slash', () => {
    const { result } = renderHook(() => useCommandPalette(commands));
    act(() => result.current.handleKeyDown(keyEvent('/'), ''));
    act(() => result.current.updateFromValue('/xh'));
    act(() => result.current.handleKeyDown(keyEvent('Backspace'), '/xh'));
    expect(result.current.open).toBe(true);
  });

  it('selectCommand returns replacement and closes', () => {
    const { result } = renderHook(() => useCommandPalette(commands));
    act(() => result.current.handleKeyDown(keyEvent('/'), ''));
    let replacement = '';
    act(() => { replacement = result.current.selectCommand(1); });
    expect(replacement).toBe('/gzh ');
    expect(result.current.open).toBe(false);
    expect(result.current.query).toBe('');
  });

  it('selectCommand returns empty string for invalid index', () => {
    const { result } = renderHook(() => useCommandPalette(commands));
    let replacement = 'x';
    act(() => { replacement = result.current.selectCommand(99); });
    expect(replacement).toBe('');
  });

  it('updateFromValue is a no-op when closed', () => {
    const { result } = renderHook(() => useCommandPalette(commands));
    act(() => result.current.updateFromValue('/anything'));
    expect(result.current.query).toBe('');
  });
});
