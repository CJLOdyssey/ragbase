import { useEffect, useRef, useState } from 'react';
import type * as React from 'react';
import { ChevronDown, ChevronUp, Loader2, Sparkles } from 'lucide-react';
import type { Message } from '../../types/AgentStudio';
import { groupThinkingNodes, ThinkingNodeItem } from './thinking';

const THINKING_STATE_META = {
  done: { icon: Sparkles, labelKey: 'teamMessage.thinkingComplete' },
  stopped: { icon: Sparkles, labelKey: 'teamMessage.thinkingStopped' },
  pending: { icon: Loader2, labelKey: 'teamMessage.thinkingPending' },
} as const;

type ThinkingState = keyof typeof THINKING_STATE_META;

function ThinkingBody({
  thinking,
  state,
  bodyRef,
  t,
}: {
  thinking: string;
  state: ThinkingState;
  bodyRef: React.RefObject<HTMLDivElement>;
  t: (key: string) => string;
}) {
  const items = groupThinkingNodes(thinking);
  const sizeClass = state === 'pending' ? 'text-xs' : 'text-base';
  return (
    <div
      className={`relative mt-2 max-h-[420px] overflow-y-auto ${sizeClass} text-[var(--color-text-muted)] leading-[1.65]`}
      ref={bodyRef}
    >
      <div className="relative pl-4">
        <div className="absolute left-2 top-0 bottom-0 w-px bg-[var(--color-border)] pointer-events-none" />
        {items.map((item, i) => (
          <ThinkingNodeItem key={i} item={item} t={t} />
        ))}
      </div>
    </div>
  );
}

export function ThinkingSection({
  msg,
  color,
  showContinue,
  t,
}: {
  msg: Message;
  color: string;
  showContinue?: boolean;
  t: (key: string) => string;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const bodyRef = useRef<HTMLDivElement>(null);
  const thinking = msg.thinking ?? '';
  const toggle = () => setIsExpanded(!isExpanded);

  useEffect(() => {
    const el = bodyRef.current;
    if (el && isExpanded) {
      el.scrollTop = el.scrollHeight;
    }
  }, [msg.thinking?.length, isExpanded]);

  if (!thinking) return null;
  const state: ThinkingState = msg.thinkingDone
    ? 'done'
    : showContinue
      ? 'stopped'
      : 'pending';
  const { icon: StateIcon, labelKey } = THINKING_STATE_META[state];

  if (state === 'stopped') {
    return (
      <div className="mb-3">
        <div className="inline-flex items-center gap-1.5 p-0 bg-none border-none cursor-default text-xs font-medium text-[var(--color-text-muted)] transition-colors duration-150 hover:text-[var(--color-text-primary)]">
          <StateIcon size={14} className={color} />
          <span>{t(labelKey)}</span>
        </div>
        <ThinkingBody
          thinking={thinking}
          state={state}
          bodyRef={bodyRef}
          t={t}
        />
      </div>
    );
  }

  return (
    <div className="mb-3">
      <button
        className="inline-flex items-center gap-1.5 p-0 bg-none border-none cursor-pointer text-xs font-medium text-[var(--color-text-muted)] transition-colors duration-150 hover:text-[var(--color-text-primary)]"
        onClick={toggle}
        aria-expanded={isExpanded}
      >
        <StateIcon size={14} className={color} />
        <span>{t(labelKey)}</span>
        {state === 'done' && (
          <span className="text-xs text-[var(--color-text-muted)] ml-1">
            {Math.max(1, Math.round(thinking.length / 50))}
            {t('teamMessage.seconds')}
          </span>
        )}
        <span className="text-xs text-[var(--color-text-muted)]">
          {isExpanded ? t('teamMessage.collapse') : t('teamMessage.expand')}
        </span>
        {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      {isExpanded && (
        <ThinkingBody
          thinking={thinking}
          state={state}
          bodyRef={bodyRef}
          t={t}
        />
      )}
    </div>
  );
}
