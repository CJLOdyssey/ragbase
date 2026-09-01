import { useEffect, useMemo, useRef } from 'react';
import type { VirtuosoHandle } from 'react-virtuoso';

/**
 * Auto-follow scroll: scrolls to bottom when messages change, pauses when user
 * scrolls up, resumes when user scrolls back to bottom.
 *
 * Uses Virtuoso's scrollToIndex API for smooth virtualized scrolling.
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
  const prevLenRef = useRef(lastMsgLen);

  useEffect(() => {
    prevLenRef.current = lastMsgLen;
    // 契约：用户上滑阅读历史（followBottom=false）时不抢滚动位置；
    // 仅跟随态才在新消息/流式内容变化时跳底。
    if (!followBottomRef.current) return;
    // Scroll to last message using Virtuoso API
    if (displayMessages.length > 0) {
      virtuosoRef.current?.scrollToIndex({
        index: displayMessages.length - 1,
        align: 'end',
        behavior: 'auto',
      });
    }
  }, [lastMsgLen, lastMsgStream, virtuosoRef, displayMessages.length]);

  useEffect(() => {
    followBottomRef.current = true;
  }, [activeConvId]);
}
