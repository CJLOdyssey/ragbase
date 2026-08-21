import { useMemo, useState } from 'react';
import Modal from '../shared/Modal';
import { useQuery } from '@tanstack/react-query';
import { FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import { listAssetChunks } from '../../api/client/assets';

interface AssetChunksModalProps {
  asset: AssetItem;
  onClose: () => void;
}

export default function AssetChunksModal({
  asset,
  onClose,
}: AssetChunksModalProps) {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const {
    data: chunks,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['asset-chunks', asset.id],
    queryFn: () => listAssetChunks(asset.id),
  });

  const pageChunks = useMemo(() => {
    if (!chunks) return [];
    const start = (page - 1) * pageSize;
    return chunks.slice(start, start + pageSize);
  }, [chunks, page]);

  const totalPages = chunks
    ? Math.max(1, Math.ceil(chunks.length / pageSize))
    : 1;

  return (
    <Modal
      title={`${t('assets.chunks.title')} · ${asset.name}`}
      onClose={onClose}
      ariaLabel={t('assets.chunks.title')}
      width={640}
      hideHeaderBorder
      bodyClassName="p-6"
      footer={
        <button
          className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-accent)] text-white hover:opacity-90"
          onClick={onClose}
        >
          {t('common.close')}
        </button>
      }
    >
      {isLoading ? (
        <div className="py-12 text-center text-sm text-[var(--color-text-muted)]">
          {t('assets.chunks.loading')}
        </div>
      ) : isError ? (
        <div className="py-12 text-center text-sm text-[var(--color-danger)]">
          {t('common.error')}
        </div>
      ) : !chunks || chunks.length === 0 ? (
        <div className="py-12 text-center">
          <FileText
            size={24}
            className="mx-auto mb-2 text-[var(--color-text-muted)]"
          />
          <p className="text-sm text-[var(--color-text-primary)] m-0">
            {t('assets.chunks.empty')}
          </p>
          <p className="text-xs text-[var(--color-text-muted)] mt-1 m-0">
            {t('assets.chunks.emptyDesc')}
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-[var(--color-text-muted)] m-0">
            {chunks.length >= 200
              ? t('assets.chunks.truncated', { count: 200 })
              : t('assets.chunks.count', { count: chunks.length })}
            {chunks.length > pageSize ? ` · 第 ${page} / ${totalPages} 页` : ''}
          </p>
          <ul
            className="flex flex-col gap-2 max-h-[420px] overflow-y-auto"
            data-testid="chunk-list"
          >
            {pageChunks.map((chunk, index) => {
              const globalIdx = (page - 1) * pageSize + index;
              return (
                <li
                  key={`${asset.id}-${globalIdx}`}
                  className="flex flex-col gap-1 p-3 rounded-lg bg-[var(--color-surface-raised)] border border-[var(--color-border)]"
                  data-testid={`chunk-${globalIdx}`}
                >
                  <div className="text-[10px] font-mono text-[var(--color-text-tertiary)]">
                    CHUNK #{globalIdx + 1}
                  </div>
                  {chunk.tags.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {chunk.tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)]"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  <p className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap break-words leading-[1.6] m-0">
                    {chunk.text}
                  </p>
                </li>
              );
            })}
          </ul>
          {chunks.length > pageSize && (
            <div className="flex items-center justify-between pt-2 border-t border-[var(--color-border-subtle)]">
              <span className="text-[11px] font-mono text-[var(--color-text-tertiary)]">
                {page * pageSize - pageSize + 1}-
                {Math.min(page * pageSize, chunks.length)} / {chunks.length}
              </span>
              <div className="flex gap-1.5">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="px-2.5 py-1 text-xs rounded border border-[var(--color-border)] bg-[var(--color-surface-raised)] disabled:opacity-50"
                >
                  上一页
                </button>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="px-2.5 py-1 text-xs rounded border border-[var(--color-border)] bg-[var(--color-surface-raised)] disabled:opacity-50"
                >
                  下一页
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
