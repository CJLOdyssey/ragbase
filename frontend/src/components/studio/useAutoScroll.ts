import { useEffect, useMemo, useRef } from 'react';

/**
 * Auto-follow scroll: scrolls to bottom when messages change, pauses when user
 * scrolls up, resumes when user scrolls back to bottom.
 */
export function useAutoScroll(
  containerRef: React.RefObject<HTMLDivElement | null>,
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
  const programmaticScrollRef = useRef(false);
  const prevLenRef = useRef(lastMsgLen);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onScroll = () => {
      if (programmaticScrollRef.current) {
        programmaticScrollRef.current = false;
        return;
      }
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 24;
      if (atBottom !== followBottomRef.current) followBottomRef.current = atBottom;
    };
    el.addEventListener('scroll', onScroll);
    return () => el.removeEventListener('scroll', onScroll);
  }, [containerRef]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const lenChanged = lastMsgLen !== prevLenRef.current;
    prevLenRef.current = lastMsgLen;
    if (!lenChanged && !followBottomRef.current) return;
    programmaticScrollRef.current = true;
    el.scrollTo({ top: el.scrollHeight, behavior: 'auto' });
  }, [lastMsgLen, lastMsgStream, containerRef]);

  useEffect(() => {
    followBottomRef.current = true;
  }, [activeConvId]);
}
