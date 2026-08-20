import { STATUS_COLORS } from '../shared/statusColors';
import {
  Braces,
  FileText,
  Image as ImageIcon,
  Pencil,
  RotateCcw,
  Search,
  Trash2,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import type { IndexProgress } from '../../api/client/assets';
import { ActionButton, ExtBadge, StatusPill } from './AssetBadges';
import { getAssetStatus, getExt, type IndexingEntry } from './assetUtils';

interface AssetsGridProps {
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

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function AssetsGrid({
  assets,
  indexing,
  progressMap,
  onPreview,
  onChunks,
  onRename,
  onDelete,
  onIndex,
  onRetry,
}: AssetsGridProps) {
  const { t } = useTranslation();
  return (
    <div className="grid gap-3.5 [grid-template-columns:repeat(auto-fill,minmax(300px,1fr))]">
      {assets.map((asset) => {
        const ext = getExt(asset.name);
        const progress = progressMap[asset.id];
        const status = getAssetStatus(asset, indexing, progress);
        const isIndexingActive = indexing.some(
          (i) => i.id === asset.id && i.deadline > Date.now(),
        );
        return (
          <div
            key={asset.id}
            onClick={() => onPreview(asset)}
            className="bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[14px] p-[18px] pb-3.5 cursor-pointer transition-all hover:border-[var(--color-border-strong)] hover:-translate-y-0.5 hover:shadow-[0_8px_32px_rgba(0,0,0,0.25)]"
            data-testid={`asset-item-${asset.id}`}
          >
            <div className="flex items-center gap-2.5 mb-2.5">
              <ExtBadge ext={ext} />
              <span
                className="text-[14px] font-semibold text-[var(--color-text-primary)] truncate flex-1 min-w-0"
                title={asset.name}
              >
                {asset.name}
              </span>
            </div>

            <div className="flex items-center gap-3 mb-3 text-[12px] text-[var(--color-text-secondary)]">
              <span className="font-mono uppercase">
                {ext || asset.assetType}
              </span>
              <span className="text-[var(--color-text-tertiary)]">·</span>
              <span className="font-mono">{formatBytes(asset.sizeBytes)}</span>
            </div>

            {status === 'processing' && progress ? (
              <div className="flex items-center gap-2 mb-3">
                <div className="flex-1 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
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
              <div className="mb-3">
                <StatusPill status={status} />
              </div>
            )}

            <div
              className="flex items-center gap-1.5 pt-3 border-t border-[var(--color-border)]"
              onClick={(e) => e.stopPropagation()}
            >
              {asset.assetType === 'document' && !asset.indexed && (
                <ActionButton
                  title={t('assets.action.index')}
                  hoverVar="--color-accent"
                  onClick={() => onIndex(asset.id)}
                  disabled={isIndexingActive}
                >
                  <Search size={12} />
                </ActionButton>
              )}
              {status === 'failed' && (
                <ActionButton
                  title={t('assets.action.retry')}
                  hoverVar="--color-accent-soft"
                  onClick={() => onRetry(asset.id)}
                >
                  <RotateCcw size={12} />
                </ActionButton>
              )}
              {asset.indexed && (
                <ActionButton
                  title={t('assets.action.chunks')}
                  hoverVar="--color-accent"
                  onClick={() => onChunks(asset)}
                >
                  <Braces size={12} />
                </ActionButton>
              )}
              <ActionButton
                title={t('assets.action.rename')}
                hoverVar="--color-accent-soft"
                onClick={() => onRename(asset)}
              >
                <Pencil size={12} />
              </ActionButton>
              <ActionButton
                title={t('assets.action.delete')}
                hoverVar="--color-danger"
                onClick={() => onDelete(asset)}
              >
                <Trash2 size={12} />
              </ActionButton>
              <div className="ml-auto text-[var(--color-text-tertiary)]">
                {asset.assetType === 'image' ? (
                  <ImageIcon size={14} />
                ) : (
                  <FileText size={14} />
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
