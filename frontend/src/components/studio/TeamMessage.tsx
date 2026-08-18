import { memo, useState } from 'react';
import {
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Eye,
  Loader2,
  Play,
  RotateCcw,
  Terminal,
  ThumbsDown,
  ThumbsUp,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import type { RagSource } from '../../types';
import type { Message } from '../../types/studio';
import { CopyBtn } from './messages/CopyBtn';
import RetrievalPanel from './RetrievalPanel';
import { markdownComponents, rehypeLinkify } from './thinking';
import { ThinkingSection } from './ThinkingSection';
import UserMessage from './UserMessage';
import VersionPager from './VersionPager';

function SourcesBlock({
  sources,
  t,
  onViewDetails,
}: {
  sources: RagSource[];
  t: (key: string, options?: Record<string, unknown>) => string;
  onViewDetails?: () => void;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  if (sources.length === 0) return null;
  return (
    <div className="mt-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raised)] overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2">
        <button
          className="flex items-center gap-2 text-xs font-medium text-[var(--color-text-secondary)] cursor-pointer bg-transparent border-none hover:text-[var(--color-text-primary)] transition-colors duration-150"
          onClick={() => setIsExpanded((v) => !v)}
          aria-expanded={isExpanded}
        >
          <span>{t('teamMessage.sources', { count: sources.length })}</span>
          {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </button>
        {onViewDetails && (
          <button
            className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-[var(--color-accent)] cursor-pointer bg-transparent border-none hover:underline transition-colors duration-150"
            onClick={onViewDetails}
            data-testid="view-details-btn"
          >
            <Eye size={12} />
            <span>{t('retrievalPanel.viewDetails')}</span>
          </button>
        )}
      </div>
      {isExpanded && (
        <ul className="p-2 flex flex-col gap-1.5">
          {sources.map((s, i) => (
            <li
              key={`${s.asset_id ?? s.asset_name ?? 'src'}-${i}`}
              className="text-xs text-[var(--color-text-secondary)] leading-relaxed"
            >
              <span className="text-[var(--color-accent)]">
                {s.asset_name || t('teamMessage.sourceAsset')}
              </span>
              {typeof s.similarity === 'number' && (
                <span className="ml-1 text-[var(--color-text-muted)]">
                  {Math.round(s.similarity * 100)}%
                </span>
              )}
              <span className="block mt-0.5 line-clamp-3 text-[var(--color-text-muted)]">
                {s.text}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function PlanCard({
  msg,
  color,
  t,
}: {
  msg: Message;
  color: string;
  t: (key: string, options?: Record<string, unknown>) => string;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const toggle = () => setIsExpanded(!isExpanded);
  if (!msg.plan) return null;

  return (
    <div className="bg-[var(--color-surface-raised)] rounded-lg overflow-hidden mt-1">
      <div
        className="flex items-center justify-between px-3 py-2 cursor-pointer transition-colors duration-150 hover:bg-[var(--color-surface-hover)]"
        onClick={toggle}
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        aria-controls="process-steps"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            toggle();
          }
        }}
      >
        <div className="flex items-center gap-2 text-xs font-medium text-[var(--color-text-secondary)]">
          <Terminal size={12} className={color} />
          {t('teamMessage.executeTask', { count: String(msg.plan.length) })}
        </div>
        {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </div>

      {isExpanded && (
        <div className="p-3 flex flex-col gap-2" id="process-steps">
          {msg.plan.map((step) => (
            <div
              key={step.step}
              className="flex items-center gap-2 text-xs text-[var(--color-text-secondary)]"
            >
              {step.status === 'completed' ? (
                <CheckCircle2
                  size={14}
                  className="text-[var(--color-success)]"
                />
              ) : (
                <Loader2 size={14} className={`${color} animate-spin`} />
              )}
              <span>{step.step}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ThumbButton({
  msg,
  value,
  onThumbsFeedback,
  t,
}: {
  msg: Message;
  value: 'up' | 'down';
  onThumbsFeedback?: (msgId: string, value: 'up' | 'down' | null) => void;
  t: (key: string) => string;
}) {
  const active = msg.thumbsFeedback === value;
  const Icon = value === 'up' ? ThumbsUp : ThumbsDown;
  const baseLabel =
    value === 'up' ? t('teamMessage.thumbsUp') : t('teamMessage.thumbsDown');
  return (
    <button
      className={`flex items-center justify-center min-w-[24px] min-h-[24px] bg-transparent border border-[var(--color-border)] rounded text-[var(--color-text-muted)] cursor-pointer transition-colors duration-150 p-0 hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]${active ? ' bg-[var(--color-accent)] !text-[var(--color-text-on-accent)] !border-[var(--color-accent)]' : ''}`}
      onClick={() => onThumbsFeedback?.(msg.id, active ? null : value)}
      title={active ? t('teamMessage.removeFeedback') : baseLabel}
      aria-label={active ? t('teamMessage.removeFeedback') : baseLabel}
    >
      <Icon size={12} />
    </button>
  );
}

function MessageActionBar({
  msg,
  time,
  onRegenerate,
  onThumbsFeedback,
  showContinue,
  isContinuing,
  onContinue,
  onSwitchVersion,
  t,
}: {
  msg: Message;
  time: string;
  onRegenerate?: (msgId: string) => void;
  onThumbsFeedback?: (msgId: string, value: 'up' | 'down' | null) => void;
  showContinue?: boolean;
  isContinuing?: boolean;
  onContinue?: () => void;
  onSwitchVersion?: (msgId: string, direction: 'prev' | 'next') => void;
  t: (key: string) => string;
}) {
  const versionTotal = msg.answerVersions?.length ?? 0;
  return (
    <div className="flex items-center gap-2 mt-1 w-full">
      <CopyBtn text={msg.content} label={t('teamMessage.copy')} />
      <button
        className="px-1 py-0.5 bg-transparent border-none rounded text-[var(--color-text-muted)] cursor-pointer flex items-center transition-colors duration-150 hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]"
        onClick={() => onRegenerate?.(msg.id)}
        title={t('teamMessage.regenerate')}
        aria-label={t('teamMessage.regenerate')}
      >
        <RotateCcw size={12} />
      </button>
      <ThumbButton
        msg={msg}
        value="up"
        onThumbsFeedback={onThumbsFeedback}
        t={t}
      />
      <ThumbButton
        msg={msg}
        value="down"
        onThumbsFeedback={onThumbsFeedback}
        t={t}
      />
      {versionTotal > 1 && (
        <VersionPager
          total={versionTotal}
          current={msg.currentAnswerVersion ?? 0}
          onPrev={() => onSwitchVersion?.(msg.id, 'prev')}
          onNext={() => onSwitchVersion?.(msg.id, 'next')}
          prevLabel="Previous answer version"
          nextLabel="Next answer version"
        />
      )}
      {time && (
        <span className="block text-xs text-[var(--color-text-muted)] mt-1 ml-0">
          {time}
        </span>
      )}
      {(showContinue || isContinuing) && (
        <button
          className={`flex items-center gap-1 px-2 py-0.5 bg-transparent border border-[var(--color-accent)] rounded-md text-[var(--color-accent)] cursor-pointer text-xs font-medium ml-auto transition-colors duration-150 hover:bg-[var(--color-accent)] hover:text-[var(--color-text-on-accent)]${isContinuing ? ' opacity-70 cursor-wait' : ''}`}
          onClick={isContinuing ? undefined : onContinue}
          disabled={isContinuing}
          title={
            isContinuing
              ? t('teamMessage.continuing')
              : t('teamMessage.continue')
          }
          aria-label={
            isContinuing
              ? t('teamMessage.continuing')
              : t('teamMessage.continue')
          }
        >
          {isContinuing ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <Play size={12} />
          )}
          <span>
            {isContinuing
              ? t('teamMessage.continuing')
              : t('teamMessage.continue')}
          </span>
        </button>
      )}
    </div>
  );
}

const TeamMessage = memo(function TeamMessage({
  msg,
  onEditMessage,
  onRegenerate,
  showContinue,
  onContinue,
  onSwitchUserVersion,
  onSwitchAnswer,
  isContinuing,
  onThumbsFeedback,
}: {
  msg: Message;
  onEditMessage?: (msgId: string, newContent: string) => void;
  onRegenerate?: (msgId: string) => void;
  showContinue?: boolean;
  onContinue?: () => void;
  onSwitchUserVersion?: (msgId: string, direction: 'prev' | 'next') => void;
  onSwitchAnswer?: (msgId: string, direction: 'prev' | 'next') => void;
  isContinuing?: boolean;
  onThumbsFeedback?: (msgId: string, value: 'up' | 'down' | null) => void;
}) {
  const { t, i18n } = useTranslation();
  const [retrievalPanelOpen, setRetrievalPanelOpen] = useState(false);
  const isUser = msg.role === 'user';

  if (isUser) {
    return (
      <UserMessage
        msg={msg}
        onEditMessage={onEditMessage}
        onSwitchUserVersion={onSwitchUserVersion}
      />
    );
  }

  const agentInfo = {
    name: t('teamMessage.unknownAgent'),
    role: t('teamMessage.system'),
    icon: Bot,
    color: 'text-[var(--color-text-muted)]',
    bg: 'bg-[var(--color-surface-raised)]',
    border: 'border-[var(--color-border)]',
  };
  const time = msg.timestamp
    ? new Date(msg.timestamp).toLocaleTimeString(
        i18n.language === 'en-US' ? 'en-US' : 'zh-CN',
        {
          hour: '2-digit',
          minute: '2-digit',
        },
      )
    : '';

  return (
    <>
      <div className="flex gap-3">
        <div className="flex flex-col gap-1 items-start max-w-full bg-[var(--color-surface)]/30 px-4 py-3 rounded-xl">
          {msg.isTyping ? (
            <div className="flex items-center gap-3 px-4 py-3 bg-[var(--color-surface-raised)] rounded-[12px_12px_12px_4px] w-fit">
              <Loader2 size={14} className={`${agentInfo.color} animate-spin`} />
              <span>{t('agent.thinking', { name: agentInfo.name })}</span>
            </div>
          ) : (
            <div style={{ animation: 'fadeInUp 0.15s ease-out' }}>
              {msg.plan ? (
                <PlanCard msg={msg} color={agentInfo.color} t={t} />
              ) : msg.action ? (
                <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
                  <CheckCircle2 size={12} className={agentInfo.color} />
                  {msg.action.label}
                </div>
              ) : null}

              <div className="flex flex-row items-start gap-2 w-full">
                <div className="flex-1 min-w-0 bg-transparent text-[var(--color-text-primary)] rounded-none p-0 text-base leading-[1.7]">
                  <ThinkingSection
                    msg={msg}
                    color={agentInfo.color}
                    showContinue={showContinue}
                    t={t}
                  />
                  <ReactMarkdown
                    rehypePlugins={[rehypeLinkify]}
                    components={markdownComponents(t)}
                  >
                    {msg.content}
                  </ReactMarkdown>
                  {msg.sources && msg.sources.length > 0 && (
                    <SourcesBlock
                      sources={msg.sources}
                      t={t}
                      onViewDetails={() => setRetrievalPanelOpen(true)}
                    />
                  )}
                </div>
              </div>

              {showContinue && !isContinuing && (
                <div className="flex items-center gap-2 pt-1 pb-0 w-full">
                  <span className="flex-1 h-px border-t border-dashed border-[var(--color-text-muted)] opacity-50" />
                  <span className="text-xs text-[var(--color-text-muted)] whitespace-nowrap select-none">
                    {t('teamMessage.interrupted')}
                  </span>
                </div>
              )}

              <MessageActionBar
                msg={msg}
                time={time}
                onRegenerate={onRegenerate}
                onThumbsFeedback={onThumbsFeedback}
                showContinue={showContinue}
                isContinuing={isContinuing}
                onContinue={onContinue}
                onSwitchVersion={onSwitchAnswer}
                t={t}
              />
            </div>
          )}
        </div>
      </div>
      <RetrievalPanel
        sources={msg.sources ?? []}
        isOpen={retrievalPanelOpen}
        onClose={() => setRetrievalPanelOpen(false)}
      />
    </>
  );
});

export default TeamMessage;
