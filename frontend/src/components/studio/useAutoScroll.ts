import { useEffect, useMemo, useRef } from 'react';
import type { VirtuosoHandle } from 'react-virtuoso';

function findScroller(): HTMLElement | null {
  return (
    document.querySelector<HTMLElement>('[data-virtuoso-scroller]') ??
    document.querySelector<HTMLElement>('[data-testid="virtuoso-scroller"]') ??
    // 兜底：找最大的 overflow:auto 容器
    Array.from(document.querySelectorAll<HTMLElement>('div')).find(
      (d) =>
        getComputedStyle(d).overflowY === 'auto' &&
        d.scrollHeight > d.clientHeight + 1,
    ) ??
    null
  );
}

function scrollVirtuosoToBottom(ref: React.RefObject<VirtuosoHandle | null>) {
  ref.current?.scrollToIndex({
    index: Infinity,
    align: 'end',
    behavior: 'auto',
  });
  const el = findScroller();
  if (el) el.scrollTop = el.scrollHeight;
}

/**
 * Auto-follow scroll: scrolls to bottom when messages change, pauses when user
 * scrolls up, resumes when user scrolls back to bottom.
 */
export function useAutoScroll(
  virtuosoRef: React.RefObject<VirtuosoHandle | null>,
  displayMessages: readonly { thinking?: string; content?: string }[],
  activeConvId: string | null,
) {
  const lastMsgLen = displayMessages.length;
  const lastMsgStream = useMemo(() => {
    const m = displayMessages[displayMessages.length - 1];
    if (!m) return '';
    return `${m.thinking ?? ''}|${m.content ?? ''}`;
  }, [displayMessages]);
  const followBottomRef = useRef(true);

  useEffect(() => {
    followBottomRef.current = true;
  }, [activeConvId]);

  useEffect(() => {
    if (!followBottomRef.current) return;
    if (displayMessages.length === 0) return;
    scrollVirtuosoToBottom(virtuosoRef);
    // 第一次滚完后 Virtuoso 可能还在计算高度，50ms 后再兜底一次
    const t = setTimeout(() => scrollVirtuosoToBottom(virtuosoRef), 50);
    return () => clearTimeout(t);
  }, [lastMsgLen, lastMsgStream, virtuosoRef, displayMessages.length]);
}
