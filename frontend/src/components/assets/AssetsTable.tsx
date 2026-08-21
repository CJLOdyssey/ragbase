import { STATUS_COLORS } from '../shared/statusColors';
import { Braces, Pencil, RotateCcw, Search, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import type { IndexProgress } from '../../api/client/assets';
import { ActionButton, ExtBadge, StatusPill } from './AssetBadges';
import { getAssetStatus, getExt, type IndexingEntry } from './assetUtils';

const GRID = 'minmax(220px,3fr) 84px 92px 116px 110px 132px 150px';

interface AssetsTableProps {
  assets: AssetItem[];
  indexing: IndexingEntry[];
  progressMap: Record<string, IndexProgress>;
  onPreview: (asset: AssetItem) => void;
  onChunks: (asset: AssetItem) => void;
  onRename: (asset: AssetItem) => void;
  onDelete: (asset: AssetItem) => void;
  onIndex: (id: string) => void;
  onRetry: (id: string) => void;
}

export default function AssetsTable({
  assets,
  indexing,
  progressMap,
  onPreview,
  onChunks,
  onRename,
  onDelete,
  onIndex,
  onRetry,
}: AssetsTableProps) {
  const { t } = useTranslation();
  const HEADERS = [
    t('assets.table.fileName'),
    t('assets.table.format'),
    t('assets.table.size'),
    t('assets.table.status'),
    t('assets.table.chunks'),
    t('assets.table.updated'),
    t('assets.table.actions'),
  ];
  return (
    <div className="rounded-[14px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] overflow-hidden">
      <div
        className="grid items-center h-10 px-[18px] border-b border-[var(--color-border-subtle)] bg-[color-mix(in_srgb,var(--color-surface-hover)_40%,transparent)]"
        style={{ gridTemplateColumns: GRID }}
      >
        {HEADERS.map((h, i) => (
          <div
            key={h}
            className={`text-[10.5px] font-semibold tracking-[0.07em] uppercase font-mono text-[var(--color-text-tertiary)] ${i === HEADERS.length - 1 ? 'text-right' : ''}`}
          >
            {h}
          </div>
        ))}
      </div>

      {assets.map((asset) => {
        const ext = getExt(asset.name);
        const progress = progressMap[asset.id];
        const status = getAssetStatus(asset, indexing, progress);
        const isProcessing = status === 'processing';
        const isIndexingActive = indexing.some(
          (i) => i.id === asset.id && i.deadline > Date.now(),
        );

        return (
          <div
            key={asset.id}
            onClick={() => onPreview(asset)}
            className="grid items-center px-[18px] h-[56px] border-b border-[var(--color-border-subtle)] hover:bg-[color-mix(in_srgb,var(--color-accent)_4%,transparent)] transition-colors cursor-pointer"
            style={{ gridTemplateColumns: GRID }}
            data-testid={`asset-item-${asset.id}`}
          >
            <div className="flex items-center gap-2.5 min-w-0 pr-3">
              <ExtBadge ext={ext} />
              <span
                className="text-[13px] text-[var(--color-text-primary)] truncate"
                title={asset.name}
              >
                {asset.name}
              </span>
            </div>

            <span className="text-[12px] font-mono uppercase text-[var(--color-text-secondary)]">
              {ext || asset.assetType}
            </span>

            <span className="text-[12px] font-mono text-[var(--color-text-secondary)]">
              {asset.sizeBytes < 1024
                ? `${asset.sizeBytes} B`
                : asset.sizeBytes < 1024 * 1024
                  ? `${(asset.sizeBytes / 1024).toFixed(1)} KB`
                  : `${(asset.sizeBytes / 1024 / 1024).toFixed(1)} MB`}
            </span>

            <div>
              <StatusPill status={status} />
            </div>

            <div className="pr-3">
              {isProcessing && progress ? (
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden min-w-[40px]">
                    <div
                      className="h-full rounded-full transition-[width] duration-300"
                      style={{
                        width: `${Math.min(progress.percentage, 100)}%`,
                        background: STATUS_COLORS.amber,
                      }}
                    />
                  </div>
                  <span className="text-[11px] font-mono text-[var(--color-text-muted)] whitespace-nowrap">
                    {progress.percentage}%
                  </span>
                </div>
              ) : (
                <span className="text-[12px] text-[var(--color-text-muted)]">
                  —
                </span>
              )}
            </div>

            <span className="text-[12px] font-mono text-[var(--color-text-muted)]">
              —
            </span>

            <div
              className="flex items-center gap-1 justify-end"
              onClick={(e) => e.stopPropagation()}
            >
              {asset.assetType === 'document' && !asset.indexed && (
                <ActionButton
                  title={t('assets.action.index')}
                  hoverVar="--color-accent"
                  onClick={() => onIndex(asset.id)}
                  disabled={isIndexingActive}
                  data-testid={`index-${asset.id}`}
                >
                  <Search size={12} />
                </ActionButton>
              )}
              {status === 'failed' && (
                <ActionButton
                  title={t('assets.action.retry')}
                  hoverVar="--color-accent-soft"
                  onClick={() => onRetry(asset.id)}
                  data-testid={`retry-${asset.id}`}
                >
                  <RotateCcw size={12} />
                </ActionButton>
              )}
              {asset.indexed && (
                <ActionButton
                  title={t('assets.action.chunks')}
                  hoverVar="--color-accent"
                  onClick={() => onChunks(asset)}
                  data-testid={`chunks-${asset.id}`}
                >
                  <Braces size={12} />
                </ActionButton>
              )}
              <ActionButton
                title={t('assets.action.rename')}
                hoverVar="--color-accent-soft"
                onClick={() => onRename(asset)}
                data-testid={`rename-${asset.id}`}
              >
                <Pencil size={12} />
              </ActionButton>
              <ActionButton
                title={t('assets.action.delete')}
                hoverVar="--color-danger"
                onClick={() => onDelete(asset)}
                data-testid={`delete-${asset.id}`}
              >
                <Trash2 size={12} />
              </ActionButton>
            </div>
          </div>
        );
      })}
    </div>
  );
}
