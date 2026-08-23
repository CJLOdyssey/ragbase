import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { useQuery } from '@tanstack/react-query';
import { Checkbox, InputNumber, Tag } from 'antd';
import { FileSearch } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { listRetrievalLogs } from '../../api/client/retrievalLogs';
import LatencyBar from './LatencyBar';
import RetrievalTable from './RetrievalTable';

const HOUR_OPTIONS = [0, 24, 72, 168];

/** 筛选工具栏 —— 自持 URL 同步；页码重置由父组件的参数派生逻辑处理。 */
function LogsToolbar({
  sinceHours,
  emptyOnly,
  maxLatency,
  onLatencyChange,
}: {
  sinceHours: number;
  emptyOnly: boolean;
  maxLatency: string;
  onLatencyChange: (v: string) => void;
}) {
  const { t } = useTranslation();
  const [, setSearchParams] = useSearchParams();

  return (
    <div className="flex items-center gap-4 mb-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-4 py-2.5">
      <div className="flex items-center gap-2">
        <span className="text-sm text-[var(--color-text-secondary)]">
          {t('retrievalLogs.timeRange')}
        </span>
        <select
          value={sinceHours}
          onChange={(e) => {
            const hours = Number(e.target.value);
            setSearchParams(
              (prev) => {
                const next = new URLSearchParams(prev);
                if (hours > 0) next.set('hours', String(hours));
                else next.delete('hours');
                return next;
              },
              { replace: true },
            );
          }}
          className="h-7 px-1.5 rounded-md border border-[var(--color-border)] bg-transparent text-xs text-[var(--color-text-secondary)] cursor-pointer"
          data-testid="logs-since-hours"
        >
          {HOUR_OPTIONS.map((h) => (
            <option key={h} value={h}>
              {h === 0
                ? t('monitoring.windowAll')
                : h === 24
                  ? t('monitoring.windowDay')
                  : h === 72
                    ? t('retrievalLogs.last72h')
                    : t('monitoring.windowWeek')}
            </option>
          ))}
        </select>
      </div>
      <div className="w-px h-4 bg-[var(--color-border)]" />
      <Checkbox
        checked={emptyOnly}
        onChange={(e) => {
          setSearchParams(
            (prev) => {
              const next = new URLSearchParams(prev);
              if (e.target.checked) next.set('empty', '1');
              else next.delete('empty');
              return next;
            },
            { replace: true },
          );
        }}
      >
        {t('retrievalLogs.emptyOnly')}
      </Checkbox>
      <div className="w-px h-4 bg-[var(--color-border)]" />
      <div className="flex items-center gap-2">
        <span className="text-sm text-[var(--color-text-secondary)]">
          {t('retrievalLogs.maxLatency')}
        </span>
        <InputNumber
          value={maxLatency ? Number(maxLatency) : null}
          placeholder="0"
          min={0}
          onChange={(v) => onLatencyChange(v == null ? '' : String(v))}
          className="w-24"
        />
        <span className="text-xs text-[var(--color-text-muted)] font-mono">
          ms
        </span>
      </div>
      <div className="ml-auto flex items-center gap-2">
        {emptyOnly && (
          <Tag color="warning" style={{ marginInlineEnd: 0 }}>
            {t('retrievalLogs.emptyRecall')}
          </Tag>
        )}
        {maxLatency && (
          <Tag color="blue" style={{ marginInlineEnd: 0 }}>
            {t('retrievalLogs.latencyFilterTag', { maxLatency })}
          </Tag>
        )}
      </div>
    </div>
  );
}

export default function RetrievalLogPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  // 下钻契约：监控页 KPI 卡通过 ?hours=&empty= 携带过滤条件直达。
  // 下钻参数直接派生为过滤态（渲染期调整，避免 effect 级联渲染）。
  const sinceHours = Number(searchParams.get('hours')) || 0;
  const emptyOnly = searchParams.get('empty') === '1';
  const paramsKey = `${sinceHours}|${emptyOnly}`;

  const [page, setPage] = useState(1);
  const [prevParamsKey, setPrevParamsKey] = useState(paramsKey);
  const [maxLatency, setMaxLatency] = useState<string>('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const pageSize = 20;

  if (prevParamsKey !== paramsKey) {
    setPrevParamsKey(paramsKey);
    if (page !== 1) setPage(1);
  }

  const { data, isLoading } = useQuery({
    queryKey: ['retrieval-logs', page, emptyOnly, maxLatency, sinceHours],
    queryFn: () =>
      listRetrievalLogs({
        page,
        page_size: pageSize,
        empty_only: emptyOnly || undefined,
        max_latency_ms: maxLatency ? Number(maxLatency) : undefined,
        since_hours: sinceHours || undefined,
      }),
  });

  const total = data?.total ?? 0;
  const totalPages = data ? Math.ceil(total / pageSize) : 0;
  const items = data?.items ?? [];

  const toggleRow = (id: string) =>
    setExpandedId((cur) => (cur === id ? null : id));

  return (
    <div className="flex flex-col h-full bg-[var(--color-surface)]">
      <div className="flex items-center justify-between px-8 py-5 border-b border-[var(--color-border)]">
        <div>
          <h1 className="text-lg font-semibold text-[var(--color-text-primary)] m-0">
            {t('retrievalLogs.title')}
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1 m-0">
            {t('retrievalLogs.subtitle')}
          </p>
        </div>
        <div className="text-xs font-mono text-[var(--color-text-muted)] px-3 py-1.5 rounded-lg bg-[var(--color-surface-raised)] border border-[var(--color-border)]">
          {t('retrievalLogs.totalCount', { total })}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 px-8 py-6">
        {!isLoading && (
          <LogsToolbar
            sinceHours={sinceHours}
            emptyOnly={emptyOnly}
            maxLatency={maxLatency}
            onLatencyChange={(v) => {
              setMaxLatency(v);
              setPage(1);
            }}
          />
        )}
        {isLoading ? (
          <LoadingState centered />
        ) : items.length === 0 ? (
          <EmptyState
            icon={<FileSearch size={24} />}
            title={t('retrievalLogs.noLogs')}
            description={t('retrievalLogs.noLogsDesc')}
            centered
          />
        ) : (
          <>
            <LatencyBar items={items} />

            <RetrievalTable
              items={items}
              expandedId={expandedId}
              onToggle={toggleRow}
            />

            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-3 mt-6">
                <button
                  className="px-3 py-1.5 rounded-md text-sm bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] border-none cursor-pointer disabled:opacity-40"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  {t('common.prev')}
                </button>
                <span className="text-sm text-[var(--color-text-muted)]">
                  {page} / {totalPages}
                </span>
                <button
                  className="px-3 py-1.5 rounded-md text-sm bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] border-none cursor-pointer disabled:opacity-40"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  {t('common.next')}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
