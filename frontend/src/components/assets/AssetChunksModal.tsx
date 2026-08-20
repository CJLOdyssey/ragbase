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
  const {
    data: chunks,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['asset-chunks', asset.id],
    queryFn: () => listAssetChunks(asset.id),
  });

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
          </p>
          <ul
            className="flex flex-col gap-2 max-h-[420px] overflow-y-auto"
            data-testid="chunk-list"
          >
            {chunks.map((chunk, index) => (
              <li
                key={`${asset.id}-${index}`}
                className="flex flex-col gap-1 p-3 rounded-lg bg-[var(--color-surface-raised)]"
                data-testid={`chunk-${index}`}
              >
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
                <p className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap break-words m-0">
                  {chunk.text}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Modal>
  );
}
