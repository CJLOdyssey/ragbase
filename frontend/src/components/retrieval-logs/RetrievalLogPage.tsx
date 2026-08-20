import { useState } from 'react';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { useQuery } from '@tanstack/react-query';
import { Checkbox, InputNumber, Tag } from 'antd';
import { FileSearch } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { listRetrievalLogs } from '../../api/client/retrievalLogs';
import LatencyBar from './LatencyBar';
import RetrievalTable from './RetrievalTable';

export default function RetrievalLogPage() {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const [emptyOnly, setEmptyOnly] = useState(false);
  const [maxLatency, setMaxLatency] = useState<string>('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const pageSize = 20;

  const { data, isLoading } = useQuery({
    queryKey: ['retrieval-logs', page, emptyOnly, maxLatency],
    queryFn: () =>
      listRetrievalLogs({
        page,
        page_size: pageSize,
        empty_only: emptyOnly || undefined,
        max_latency_ms: maxLatency ? Number(maxLatency) : undefined,
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

            <div className="flex items-center gap-4 mb-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-4 py-2.5">
              <Checkbox
                checked={emptyOnly}
                onChange={(e) => {
                  setEmptyOnly(e.target.checked);
                  setPage(1);
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
                  onChange={(v) => {
                    setMaxLatency(v == null ? '' : String(v));
                    setPage(1);
                  }}
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
