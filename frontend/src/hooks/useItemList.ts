import { useState } from 'react';

interface Item {
  id: string;
  enabled: boolean;
}

export function useItemList<T extends Item>(presets: T[]) {
  const [items, setItems] = useState<T[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);

  const toggle = (id: string) => {
    setItems((prev) => {
      const existing = prev.find((i) => i.id === id);
      if (existing) return prev.map((i) => (i.id === id ? { ...i, enabled: !i.enabled } : i));
      const preset = presets.find((p) => p.id === id);
      return preset ? [...prev, { ...preset, enabled: true }] : prev;
    });
  };

  const addCustom = (createItem: () => T) => {
    const item = createItem();
    setItems((prev) =>
      prev.some((i) => i.id === item.id) ? prev : [...prev, item],
    );
  };

  const update = (id: string, updates: Partial<T>) => {
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, ...updates } : i)));
  };

  const remove = (id: string) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
    if (editingId === id) setEditingId(null);
  };

  const getEnabledCount = (): number => items.filter((i) => i.enabled).length;

  return { items, setItems, editingId, setEditingId, toggle, addCustom, update, remove, getEnabledCount };
}
