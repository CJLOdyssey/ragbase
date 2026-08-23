import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { fetchTopQueries } from '../../api/client/monitoring';
import type { TimeRangeQuery, TopQueryKind } from '../../types/monitoring';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';

interface Props {
  timeQuery: TimeRangeQuery;
}

const KINDS: Array<{ kind: TopQueryKind; key: string }> = [
  { kind: 'empty', key: 'monitoring.topQueries.tabEmpty' },
  { kind: 'slow', key: 'monitoring.topQueries.tabSlow' },
];

/**
 * 问题查询 Top N 表：零召回（语料缺口）/ 最慢（性能热点）两个切片。
 * 行点击沿用监控页既有下钻契约 → /retrieval-logs?hours=&empty=。
 */
export default function TopQueriesTable({ timeQuery }: Props) {
  const { t } = useTranslation();
  const [kind, setKind] = useState<TopQueryKind>('empty');
  const rangeKey = timeQuery.since ? `${timeQuery.since}-${timeQuery.until}` : timeQuery.window_hours;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['monitoring-top-queries', rangeKey, kind],
    queryFn: () =>
      fetchTopQueries({
        window_hours: timeQuery.window_hours,
        since: timeQuery.since,
        until: timeQuery.until,
        kind,
        limit: 10,
      }),
  });

  // 下钻契约：预设窗口带 hours 过滤；自定义范围不带（检索记录页暂无区间参数）。
  const drillBase = timeQuery.since
    ? '/retrieval-logs'
    : `/retrieval-logs?hours=${timeQuery.window_hours}`;

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-5">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="m-0 text-sm font-medium text-[var(--color-text-primary)]">
          {t('monitoring.topQueries.title')}
        </h3>
        <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-0.5">
          {KINDS.map((k) => (
            <button
              key={k.kind}
              type="button"
              className={`px-2.5 py-1 rounded-md text-xs cursor-pointer border-none transition-colors duration-150 ${
                kind === k.kind
                  ? 'bg-[var(--color-accent)] text-[var(--color-text-on-accent)]'
                  : 'bg-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
              }`}
              onClick={() => setKind(k.kind)}
              data-testid={`topq-tab-${k.kind}`}
            >
              {t(k.key)}
            </button>
          ))}
        </div>
      </div>

      {isError ? (
        <EmptyState
          title={t('monitoring.loadFailed')}
          action={
            <button
              type="button"
              className="px-3 py-1.5 rounded-md text-sm cursor-pointer border-none bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
              onClick={() => void refetch()}
            >
              {t('common.retry')}
            </button>
          }
          centered
        />
      ) : isLoading || !data ? (
        <LoadingState centered />
      ) : data.items.length === 0 ? (
        <EmptyState
          title={t('monitoring.noData')}
          description={t('monitoring.topQueries.emptyDesc')}
          centered
        />
      ) : (
        <div className="flex flex-col" data-testid="topq-list">
          <div className="flex items-center gap-3 px-2 pb-1.5 font-mono text-[10px] text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
            <span className="w-6 shrink-0">#</span>
            <span className="flex-1">{t('monitoring.topQueries.query')}</span>
            <span className="w-14 shrink-0 text-right">
              {t('monitoring.topQueries.count')}
            </span>
            {kind === 'slow' && (
              <span className="w-20 shrink-0 text-right">
                {t('monitoring.topQueries.avgLatency')}
              </span>
            )}
          </div>
          {data.items.map((item, idx) => (
            <Link
              key={`${item.query}-${idx}`}
              to={kind === 'empty' ? `${drillBase}&empty=1` : drillBase}
              className="flex items-center gap-3 px-2 py-2 rounded-md no-underline hover:bg-[var(--color-surface-hover)] transition-colors duration-150"
              data-testid={`topq-row-${idx}`}
            >
              <span className="w-6 shrink-0 font-mono text-xs text-[var(--color-text-muted)] tabular-nums">
                {idx + 1}
              </span>
              <span
                className="flex-1 truncate text-sm text-[var(--color-text-primary)]"
                title={item.query}
              >
                {item.query || '—'}
              </span>
              <span className="w-14 shrink-0 text-right font-mono text-xs text-[var(--color-text-secondary)] tabular-nums">
                {item.count}
              </span>
              {kind === 'slow' && (
                <span className="w-20 shrink-0 text-right font-mono text-xs tabular-nums text-[var(--color-warning)]">
                  {item.avg_latency_ms != null
                    ? `${item.avg_latency_ms}ms`
                    : '—'}
                </span>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
