import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronRight, FileSearch, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { listRetrievalLogs, type RetrievalLogItem } from '../../api/client/retrievalLogs';

function latencyColor(ms: number): string {
  if (ms < 1000) return 'var(--color-accent)';
  if (ms < 3000) return 'var(--color-warning, #d97706)';
  return 'var(--color-danger, #dc2626)';
}

function SourceRow({ sources }: { sources: RetrievalLogItem['sources'] }) {
  const [open, setOpen] = useState(false);
  if (!sources || sources.length === 0) return null;
  return (
    <div className="mt-2">
      <button
        className="flex items-center gap-1 text-xs text-[var(--color-accent)] bg-transparent border-none cursor-pointer hover:underline"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        {sources.length} sources
      </button>
      {open && (
        <ul className="mt-1 flex flex-col gap-1 pl-4">
          {sources.map((s, i) => (
            <li key={`${s.asset_id ?? i}`} className="text-xs text-[var(--color-text-muted)]">
              <span className="text-[var(--color-text-secondary)]">{s.asset_name}</span>
              {typeof s.similarity === 'number' && (
                <span className="ml-2 text-[var(--color-text-muted)]">
                  {Math.round(s.similarity * 100)}%
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function RetrievalLogPage() {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const [emptyOnly, setEmptyOnly] = useState(false);
  const [maxLatency, setMaxLatency] = useState<string>('');
  const [selectedLog, setSelectedLog] = useState<RetrievalLogItem | null>(null);
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

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)]">
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)] m-0">
          {t('retrievalLogs.title')}
        </h1>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 p-6">
        <div className="flex items-center gap-4 mb-4">
          <label className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)] cursor-pointer">
            <input
              type="checkbox"
              checked={emptyOnly}
              onChange={(e) => { setEmptyOnly(e.target.checked); setPage(1); }}
              className="rounded"
            />
            {t('retrievalLogs.emptyOnly')}
          </label>
          <label className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
            {t('retrievalLogs.maxLatency')}
            <input
              type="number"
              value={maxLatency}
              onChange={(e) => { setMaxLatency(e.target.value); setPage(1); }}
              className="w-24 px-2 py-1 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
              placeholder="0"
            />
            <span className="text-xs text-[var(--color-text-muted)]">ms</span>
          </label>
        </div>

        {isLoading ? (
          <LoadingState centered={true} />
        ) : !data || data.items.length === 0 ? (
          <EmptyState
            icon={<FileSearch size={24} />}
            title={t('retrievalLogs.noLogs')}
            description={t('retrievalLogs.noLogsDesc')}
            centered={true}
          />
        ) : (
          <>
            <ul className="flex flex-col gap-2">
              {data.items.map((item) => (
                <li
                  key={item.id}
                  className="flex flex-col gap-1 px-4 py-3 rounded-lg bg-[var(--color-surface-raised)] cursor-pointer hover:bg-[var(--color-surface-hover)] transition-colors"
                  onClick={() => setSelectedLog(item)}
                >
                  <div className="flex items-center gap-4 text-sm">
                    <span className="flex-1 min-w-0 truncate text-[var(--color-text-primary)]" title={item.query}>
                      {item.query}
                    </span>
                    <span
                      className="shrink-0 text-xs font-medium"
                      style={{ color: item.hit_count === 0 ? 'var(--color-danger, #dc2626)' : 'var(--color-text-muted)' }}
                    >
                      {t('retrievalLogs.hitCount')}: {item.hit_count}
                    </span>
                    <span
                      className="shrink-0 text-xs font-medium"
                      style={{ color: latencyColor(item.latency_ms) }}
                    >
                      {item.latency_ms}ms
                    </span>
                    <span className="shrink-0 text-xs text-[var(--color-text-muted)]">
                      {new Date(item.created_at).toLocaleString()}
                    </span>
                  </div>
                  {item.sources && item.sources.length > 0 && (
                    <div className="text-xs text-[var(--color-text-muted)]">
                      {item.sources.map((s) => s.asset_name).filter(Boolean).join(', ')}
                      <SourceRow sources={item.sources} />
                    </div>
                  )}
                </li>
              ))}
            </ul>

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

      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="flex flex-col w-full max-w-3xl max-h-[80vh] rounded-lg bg-[var(--color-surface-raised)] shadow-xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)]">
              <h2 className="text-base font-semibold text-[var(--color-text-primary)] m-0">
                {t('retrievalLogs.detail')}
              </h2>
              <button
                className="text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] bg-transparent border-none cursor-pointer"
                onClick={() => setSelectedLog(null)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              <div className="flex flex-col gap-4">
                <div>
                  <label className="text-xs font-medium text-[var(--color-text-muted)]">
                    {t('retrievalLogs.query')}
                  </label>
                  <p className="text-sm text-[var(--color-text-primary)] mt-1 break-words">
                    {selectedLog.query}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-[var(--color-text-muted)]">
                      {t('retrievalLogs.hitCount')}
                    </label>
                    <p className="text-sm text-[var(--color-text-primary)] mt-1">
                      {selectedLog.hit_count}
                    </p>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-[var(--color-text-muted)]">
                      {t('retrievalLogs.latency')}
                    </label>
                    <p className="text-sm text-[var(--color-text-primary)] mt-1">
                      {selectedLog.latency_ms}ms
                    </p>
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-[var(--color-text-muted)]">
                    {t('retrievalLogs.time')}
                  </label>
                  <p className="text-sm text-[var(--color-text-primary)] mt-1">
                    {new Date(selectedLog.created_at).toLocaleString()}
                  </p>
                </div>
                {selectedLog.sources && selectedLog.sources.length > 0 && (
                  <div>
                    <label className="text-xs font-medium text-[var(--color-text-muted)]">
                      {t('retrievalLogs.sourceDetail')}
                    </label>
                    <ul className="mt-2 flex flex-col gap-2">
                      {selectedLog.sources.map((s, i) => (
                        <li key={`${s.asset_id ?? i}`} className="flex items-center gap-2 px-3 py-2 rounded-md bg-[var(--color-surface)]">
                          <span className="flex-1 text-sm text-[var(--color-text-primary)]">
                            {s.asset_name}
                          </span>
                          {typeof s.similarity === 'number' && (
                            <span className="text-xs text-[var(--color-text-muted)]">
                              {Math.round(s.similarity * 100)}%
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
