import { useRef } from 'react';
import { createPortal } from 'react-dom';
import { STATUS_COLORS } from '../shared/statusColors';
import {
  Braces,
  Download,
  FileImage,
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
  MoreHorizontal,
  Pencil,
  RotateCcw,
  Search,
  Trash2,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import type { IndexProgress } from '../../api/client/assets';
import { DataGrid } from '../shared/list';
import { useRowMenu } from '../shared/list/useRowMenu';
import { ActionButton, StatusPill } from './AssetBadges';
import {
  extColorOf,
  getAssetStatus,
  getExt,
  type IndexingEntry,
} from './assetUtils';

function FileTypeIcon({ ext }: { ext: string }) {
  const color = extColorOf(ext);
  const style = {
    color,
    background: `color-mix(in srgb, ${color} 12%, transparent)`,
    border: `1px solid color-mix(in srgb, ${color} 24%, transparent)`,
  } as React.CSSProperties;
  const isSheet = ['xlsx', 'xls', 'csv'].includes(ext);
  const isImage = ['png', 'jpg', 'jpeg', 'webp', 'gif'].includes(ext);
  return (
    <span
      className="inline-flex items-center justify-center h-7 w-7 rounded-[7px] shrink-0"
      style={style}
    >
      {isSheet ? (
        <FileSpreadsheet size={14} />
      ) : isImage ? (
        <FileImage size={14} />
      ) : (
        <FileText size={14} />
      )}
    </span>
  );
}

interface AssetsGridProps {
  assets: AssetItem[];
  indexing: IndexingEntry[];
  progressMap: Record<string, IndexProgress>;
  onPreview: (asset: AssetItem) => void;
  onChunks: (asset: AssetItem) => void;
  onRename: (asset: AssetItem) => void;
  onDelete: (asset: AssetItem) => void;
  onDownload?: (asset: AssetItem) => void;
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
  onDownload,
  onIndex,
  onRetry,
}: AssetsGridProps) {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  // Row-menu state machine shared across list pages (DIP).
  const menu = useRowMenu({ containerRef, menuRef });

  const renderCard = (asset: AssetItem) => {
    const ext = getExt(asset.name);
    const progress = progressMap[asset.id];
    const status = getAssetStatus(asset, indexing, progress);
    const isIndexingActive = indexing.some(
      (i) => i.id === asset.id && i.deadline > Date.now(),
    );
    return (
      <div
        onClick={() => onPreview(asset)}
        className="bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[14px] p-[18px] pb-3.5 cursor-pointer transition-all hover:border-[var(--color-border-strong)] hover:-translate-y-0.5 hover:shadow-[0_8px_32px_rgba(0,0,0,0.25)]"
        data-testid={`asset-item-${asset.id}`}
      >
        <div className="flex items-center gap-2.5 mb-2.5">
          <FileTypeIcon ext={ext} />
          <span
            className="text-[14px] font-semibold text-[var(--color-text-primary)] truncate flex-1 min-w-0"
            title={asset.name}
          >
            {asset.name}
          </span>
        </div>

        <div className="flex items-center gap-3 mb-3 text-[12px] text-[var(--color-text-secondary)]">
          <span className="font-mono uppercase">{ext || asset.assetType}</span>
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
          className="flex items-center gap-1.5 pt-3 border-t border-[var(--color-border)] relative"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="text-[var(--color-text-tertiary)]">
            {asset.assetType === 'image' ? (
              <ImageIcon size={14} />
            ) : (
              <FileText size={14} />
            )}
          </div>
          <div className="ml-auto flex items-center gap-1.5">
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
            {asset.assetType === 'image' ? null : status === 'failed' ? (
              <ActionButton
                title={t('assets.action.retry')}
                hoverVar="--color-accent-soft"
                onClick={() => onRetry(asset.id)}
                data-testid={`retry-${asset.id}`}
              >
                <RotateCcw size={12} />
              </ActionButton>
            ) : null}
            {asset.assetType === 'document' && (
              <ActionButton
                title={t('assets.action.chunks')}
                hoverVar="--color-accent"
                onClick={() => onChunks(asset)}
                data-testid={`chunks-${asset.id}`}
              >
                <Braces size={12} />
              </ActionButton>
            )}
            <div ref={(el) => menu.registerTrigger(asset.id, el)}>
              <ActionButton
                title="更多"
                hoverVar="--color-accent-soft"
                onClick={() => menu.toggle(asset.id)}
                data-testid={`more-${asset.id}`}
              >
                <MoreHorizontal size={12} />
              </ActionButton>
              {menu.openId === asset.id &&
                menu.pos &&
                createPortal(
                  <div
                    ref={menuRef}
                    style={{
                      position: 'fixed',
                      top: menu.pos.top,
                      right: menu.pos.right,
                    }}
                    className="z-50 min-w-[140px] rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] shadow-xl py-1"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      type="button"
                      onClick={() => {
                        menu.close();
                        onRename(asset);
                      }}
                      className="w-full text-left px-3 py-1.5 text-sm hover:bg-[var(--color-surface-hover)] flex items-center gap-2"
                      data-testid={`rename-${asset.id}`}
                    >
                      <Pencil size={12} /> {t('assets.action.rename')}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        menu.close();
                        onDownload?.(asset);
                      }}
                      className="w-full text-left px-3 py-1.5 text-sm hover:bg-[var(--color-surface-hover)] flex items-center gap-2"
                      data-testid={`download-${asset.id}`}
                    >
                      <Download size={12} /> 下载
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        menu.close();
                        onDelete(asset);
                      }}
                      className="w-full text-left px-3 py-1.5 text-sm text-[var(--color-danger)] hover:bg-[var(--color-surface-hover)] flex items-center gap-2"
                      data-testid={`delete-${asset.id}`}
                    >
                      <Trash2 size={12} /> {t('assets.action.delete')}
                    </button>
                  </div>,
                  document.body,
                )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div ref={containerRef}>
      <DataGrid<AssetItem>
        items={assets}
        itemKey={(a) => a.id}
        renderItem={renderCard}
      />
    </div>
  );
}
