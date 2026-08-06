import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useItemList } from '../useItemList';

interface MockItem { id: string; enabled: boolean; label: string }

const presets: MockItem[] = [{ id: 'p1', enabled: false, label: 'P1' }, { id: 'p2', enabled: false, label: 'P2' }];

describe('useItemList', { tags: ['unit'] }, () => {
  it('toggles an existing item', () => {
    const { result } = renderHook(() => useItemList<MockItem>(presets));
    act(() => result.current.toggle('p1'));
    expect(result.current.items).toEqual([{ id: 'p1', enabled: true, label: 'P1' }]);
    act(() => result.current.toggle('p1'));
    expect(result.current.items[0].enabled).toBe(false);
  });

  it('adds a preset item when toggling an unknown id, ignores unknown ids', () => {
    const { result } = renderHook(() => useItemList<MockItem>(presets));
    act(() => result.current.toggle('unknown'));
    expect(result.current.items).toHaveLength(0);
    act(() => result.current.toggle('p2'));
    expect(result.current.items).toHaveLength(1);
    act(() => result.current.toggle('p3'));
    expect(result.current.items).toHaveLength(1);
  });

  it('addCustom skips duplicates', () => {
    const { result } = renderHook(() => useItemList<MockItem>(presets));
    const item = { id: 'c1', enabled: false, label: 'C1' };
    act(() => result.current.addCustom(() => item));
    act(() => result.current.addCustom(() => item));
    expect(result.current.items).toHaveLength(1);
  });

  it('update merges partial changes', () => {
    const { result } = renderHook(() => useItemList<MockItem>(presets));
    act(() => result.current.toggle('p1'));
    act(() => result.current.update('p1', { label: 'Renamed' }));
    expect(result.current.items[0].label).toBe('Renamed');
  });

  it('remove filters items and clears editingId', () => {
    const { result } = renderHook(() => useItemList<MockItem>(presets));
    act(() => result.current.setEditingId('p1'));
    act(() => result.current.toggle('p1'));
    act(() => result.current.remove('p1'));
    expect(result.current.items).toHaveLength(0);
    expect(result.current.editingId).toBeNull();
  });

  it('getEnabledCount counts enabled items', () => {
    const { result } = renderHook(() => useItemList<MockItem>(presets));
    act(() => result.current.setItems([{ id: 'a', enabled: true, label: 'A' }, { id: 'b', enabled: false, label: 'B' }]));
    expect(result.current.getEnabledCount()).toBe(1);
  });
});
