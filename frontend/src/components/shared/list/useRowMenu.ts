/**
 * useRowMenu — "more" row-menu state machine (SRP).
 *
 * Owns: open id, portal position computed from the trigger's bounding rect,
 * and outside-click dismissal. Positioning/click concerns stay here so list
 * rows only compose menu items.
 */
import { useEffect, useRef, useState } from 'react';

export interface RowMenuPosition {
  top: number;
  right: number;
}

interface Options {
  /** Container ref — clicks inside it do NOT close the menu. */
  containerRef?: React.RefObject<HTMLElement | null>;
  /** Menu ref — clicks inside the portal menu do NOT close it. */
  menuRef?: React.RefObject<HTMLElement | null>;
}

export function useRowMenu({ containerRef, menuRef }: Options = {}) {
  const [openId, setOpenId] = useState<string | null>(null);
  const [pos, setPos] = useState<RowMenuPosition | null>(null);
  const triggerRefs = useRef<Map<string, HTMLElement>>(new Map());

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (menuRef?.current && menuRef.current.contains(target)) return;
      if (containerRef?.current && containerRef.current.contains(target))
        return;
      setOpenId(null);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [containerRef, menuRef]);

  const registerTrigger = (id: string, el: HTMLElement | null) => {
    if (el) triggerRefs.current.set(id, el);
    else triggerRefs.current.delete(id);
  };

  /** Toggle the menu for `id`, computing position from its trigger. */
  const toggle = (id: string) => {
    const el = triggerRefs.current.get(id);
    if (el) {
      const rect = el.getBoundingClientRect();
      setPos({
        top: rect.bottom + 6,
        right: window.innerWidth - rect.right,
      });
    }
    setOpenId((cur) => (cur === id ? null : id));
  };

  const close = () => setOpenId(null);

  return { openId, pos, registerTrigger, toggle, close };
}
