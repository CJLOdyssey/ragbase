import { Tag } from 'antd';
import { ChevronDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { RetrievalLogItem } from '../../api/client/retrievalLogs';
import {
  LATENCY_AMBER,
  LATENCY_GREEN,
  LATENCY_RED,
  latencyColor,
} from './latency';

const GRID =
  'grid grid-cols-[minmax(0,3fr)_110px_100px_90px_130px_36px] items-center';

interface RetrievalTableProps {
  items: RetrievalLogItem[];
  expandedId: string | null;
  onToggle: (id: string) => void;
}

function pillStyle(color: string) {
  return {
    color,
    borderColor: `${color}55`,
    background: `${color}1f`,
    marginInlineEnd: 0,
  };
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

function knowledgeBase(item: RetrievalLogItem): string {
  return item.sources?.[0]?.asset_name ?? '—';
}

export default function RetrievalTable({
  items,
  expandedId,
  onToggle,
}: RetrievalTableProps) {
  const { t } = useTranslation();
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] overflow-hidden">
      <div
        className={`${GRID} px-[18px] h-[44px] border-b border-[var(--color-border)] text-[11px] font-medium uppercase tracking-wide text-[var(--color-text-muted)]`}
      >
        <span>{t('retrievalLogs.query')}</span>
        <span>{t('retrievalLogs.knowledgeBase')}</span>
        <span>{t('retrievalLogs.hitCount')}</span>
        <span>{t('retrievalLogs.latency')}</span>
        <span>{t('retrievalLogs.time')}</span>
        <span />
      </div>
      {items.map((item) => {
        const expanded = expandedId === item.id;
        const kb = knowledgeBase(item);
        const hitColor = item.hitCount === 0 ? LATENCY_RED : LATENCY_GREEN;
        return (
          <div
            key={item.id}
            className="border-b border-[var(--color-border)] last:border-b-0"
          >
            <div
              onClick={() => onToggle(item.id)}
              className={`${GRID} px-[18px] h-[50px] cursor-pointer transition-colors hover:bg-[var(--color-surface-hover)] ${expanded ? 'bg-[var(--color-surface-hover)]' : ''}`}
            >
              <div className="flex items-center gap-2 min-w-0">
                {item.hitCount === 0 && (
                  <span
                    className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ background: LATENCY_AMBER }}
                  />
                )}
                <span className="truncate text-[13px] text-[var(--color-text-primary)]">
                  {item.query}
                </span>
              </div>
              <div className="min-w-0">
                <div className="truncate text-xs text-[var(--color-text-secondary)]">
                  {kb}
                </div>
                {item.sources && item.sources.length > 0 && (
                  <span className="text-xs text-[var(--color-text-muted)]">
                    {item.sources.length} sources
                  </span>
                )}
              </div>
              <Tag style={pillStyle(hitColor)}>
                {t('retrievalLogs.hitCountTag', { count: item.hitCount })}
              </Tag>
              <Tag style={pillStyle(latencyColor(item.latencyMs))}>
                {item.latencyMs}ms
              </Tag>
              <span className="text-xs text-[var(--color-text-muted)] font-mono">
                {formatTime(item.createdAt)}
              </span>
              <span
                className="flex justify-center text-[var(--color-text-muted)]"
                style={{
                  transform: expanded ? 'rotate(180deg)' : 'none',
                  transition: 'transform .15s',
                }}
              >
                <ChevronDown size={16} />
              </span>
            </div>
            {expanded && <ExpandedDetail item={item} kb={kb} />}
          </div>
        );
      })}
    </div>
  );
}

function ExpandedDetail({ item, kb }: { item: RetrievalLogItem; kb: string }) {
  const { t } = useTranslation();
  const kv: Array<[string, string]> = [
    [t('retrievalLogs.query'), item.query],
    [t('retrievalLogs.knowledgeBase'), kb],
    [
      t('retrievalLogs.hitBlocks'),
      t('retrievalLogs.hitBlocksValue', { count: item.hitCount }),
    ],
    [t('retrievalLogs.respLatency'), `${item.latencyMs} ms`],
    [t('retrievalLogs.time'), formatTime(item.createdAt)],
  ];
  return (
    <div className="px-[18px] pb-4 pt-1 bg-[var(--color-surface)]">
      <div className="text-[10px] font-mono uppercase tracking-wider text-[var(--color-text-muted)] mb-2">
        {t('retrievalLogs.detailTitle')}
      </div>
      <div className="flex flex-wrap gap-x-8 gap-y-3 mb-4">
        {kv.map(([k, v]) => (
          <div key={k}>
            <div className="text-[10px] text-[var(--color-text-muted)] mb-1 font-mono">
              {k}
            </div>
            <div className="text-[13px] text-[var(--color-text-secondary)] break-words">
              {v}
            </div>
          </div>
        ))}
      </div>
      {item.hitCount > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-wider text-[var(--color-text-muted)] mb-2">
            {t('retrievalLogs.chunkSection')}
          </div>
          <div className="flex flex-col gap-2">
            {(item.sources ?? []).slice(0, 3).map((s, i) => (
              <div
                key={s.asset_id ?? i}
                className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-3 py-2 text-xs text-[var(--color-text-secondary)] leading-relaxed"
              >
                <span className="font-mono text-[var(--color-text-muted)] mr-2">
                  CHUNK #{i + 1}
                </span>
                {s.asset_name}
                {typeof s.similarity === 'number' && (
                  <span className="ml-2 text-[var(--color-text-muted)]">
                    {Math.round(s.similarity * 100)}%
                  </span>
                )}
              </div>
            ))}
            {item.sources && item.sources.length > 3 && (
              <div className="text-xs text-[var(--color-text-muted)] text-center">
                {t('retrievalLogs.moreChunks', {
                  count: item.sources.length - 3,
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
