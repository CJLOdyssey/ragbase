import { useRef } from 'react';
import { createPortal } from 'react-dom';
import { DataTable, type DataTableColumn } from '../shared/list';
import { useRowMenu } from '../shared/list/useRowMenu';
import { STATUS_COLORS } from '../shared/statusColors';
import {
  Braces,
  Download,
  FileImage,
  FileSpreadsheet,
  FileText,
  MoreHorizontal,
  Pencil,
  RotateCcw,
  Search,
  Trash2,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import type { IndexProgress } from '../../api/client/assets';
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
  const iconProps = { size: 14 } as const;
  const isSheet = ['xlsx', 'xls', 'csv'].includes(ext);
  const isImage = ['png', 'jpg', 'jpeg', 'webp', 'gif'].includes(ext);
  return (
    <span
      className="inline-flex items-center justify-center h-7 w-7 rounded-[7px] shrink-0"
      style={style}
    >
      {isSheet ? (
        <FileSpreadsheet {...iconProps} />
      ) : isImage ? (
        <FileImage {...iconProps} />
      ) : (
        <FileText {...iconProps} />
      )}
    </span>
  );
}

interface AssetsTableProps {
  assets: AssetItem[];
  indexing: IndexingEntry[];
  progressMap: Record<string, IndexProgress>;
  sortField?: string | null;
  sortDir?: 'asc' | 'desc';
  onSort?: (field: string) => void;
  onPreview: (asset: AssetItem) => void;
  onChunks: (asset: AssetItem) => void;
  onRename: (asset: AssetItem) => void;
  onDelete: (asset: AssetItem) => void;
  onDownload?: (asset: AssetItem) => void;
  onIndex: (id: string) => void;
  onRetry: (id: string) => void;
}

function formatUpdatedAt(v?: string | null): string {
  if (!v) return '—';
  try {
    const d = new Date(v);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${day} ${hh}:${mm}`;
  } catch {
    return '—';
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** Centered cell wrapper matching assets visual baseline. */
function CellCenter({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-center text-center min-w-0">
      {children}
    </div>
  );
}

export default function AssetsTable({
  assets,
  indexing,
  progressMap,
  sortField,
  sortDir,
  onSort,
  onPreview,
  onChunks,
  onRename,
  onDelete,
  onDownload,
  onIndex,
  onRetry,
}: AssetsTableProps) {
  const { t } = useTranslation();
  const menuRef = useRef<HTMLDivElement>(null);

  // Row-menu state machine shared with prompts/admin lists (DIP).
  const menu = useRowMenu({ menuRef });
  const openId = menu.openId;

  const columns: DataTableColumn[] = [
    {
      key: 'name',
      header: t('assets.table.fileName'),
      width: 'minmax(160px,1.5fr)',
      sortable: true,
    },
    {
      key: 'format',
      header: t('assets.table.format'),
      width: '84px',
      sortable: true,
    },
    {
      key: 'size',
      header: t('assets.table.size'),
      width: '96px',
      sortable: true,
    },
    {
      key: 'status',
      header: t('assets.table.status'),
      width: '110px',
      sortable: true,
    },
    {
      key: 'chunks',
      header: t('assets.table.chunks'),
      width: '92px',
      sortable: true,
    },
    {
      key: 'updated',
      header: t('assets.table.updated'),
      width: '148px',
      sortable: true,
    },
    { key: 'actions', header: t('assets.table.actions'), width: '112px' },
  ];

  const renderActionsCell = (asset: AssetItem): React.ReactNode => {
    const status = getAssetStatus(asset, indexing, progressMap[asset.id]);
    const isIndexingActive = indexing.some(
      (i) => i.id === asset.id && i.deadline > Date.now(),
    );
    return (
      <div
        className="flex items-center gap-1 justify-center relative"
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
        {asset.assetType === 'document' && status === 'failed' && (
          <ActionButton
            title={t('assets.action.retry')}
            hoverVar="--color-accent-soft"
            onClick={() => onRetry(asset.id)}
            data-testid={`retry-${asset.id}`}
          >
            <RotateCcw size={12} />
          </ActionButton>
        )}
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
          {openId === asset.id &&
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
    );
  };

  const renderChunksCell = (asset: AssetItem): React.ReactNode => {
    const progress = progressMap[asset.id];
    const status = getAssetStatus(asset, indexing, progress);
    const isProcessing = status === 'processing';
    return (
      <CellCenter>
        {asset.assetType === 'image' ? (
          <span className="text-[12px] text-[var(--color-text-muted)]">—</span>
        ) : isProcessing && progress ? (
          <div className="flex items-center gap-2 justify-center">
            <div className="flex-1 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden min-w-[40px] max-w-[60px]">
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
        ) : asset.chunkCount != null ? (
          <span className="text-[12px] font-mono text-[var(--color-text-secondary)]">
            {asset.chunkCount}
          </span>
        ) : (
          <span className="text-[12px] text-[var(--color-text-muted)]">—</span>
        )}
      </CellCenter>
    );
  };

  const renderCell = (
    asset: AssetItem,
    col: DataTableColumn,
  ): React.ReactNode => {
    const ext = getExt(asset.name);
    switch (col.key) {
      case 'name':
        return (
          <div className="flex items-center gap-2.5 min-w-0 pr-3">
            <FileTypeIcon ext={ext} />
            <span
              className="text-[13px] text-[var(--color-text-primary)] truncate"
              title={asset.name}
            >
              {asset.name}
            </span>
          </div>
        );
      case 'format':
        return (
          <CellCenter>
            <span className="text-[12px] font-mono uppercase text-[var(--color-text-secondary)]">
              {ext || asset.assetType}
            </span>
          </CellCenter>
        );
      case 'size':
        return (
          <CellCenter>
            <span className="text-[12px] font-mono text-[var(--color-text-secondary)]">
              {formatSize(asset.sizeBytes)}
            </span>
          </CellCenter>
        );
      case 'status': {
        const status = getAssetStatus(asset, indexing, progressMap[asset.id]);
        return (
          <CellCenter>
            <StatusPill status={status} />
          </CellCenter>
        );
      }
      case 'chunks':
        return renderChunksCell(asset);
      case 'updated':
        return (
          <CellCenter>
            <span className="text-[11px] font-mono text-[var(--color-text-muted)]">
              {formatUpdatedAt(asset.updatedAt)}
            </span>
          </CellCenter>
        );
      case 'actions':
        return renderActionsCell(asset);
      default:
        return null;
    }
  };

  return (
    <DataTable<AssetItem>
      rows={assets}
      columns={columns}
      rowKey={(a) => a.id}
      renderCell={(row, col) => renderCell(row, col)}
      onRowClick={(a) => onPreview(a)}
      rowTestId={(a) => `asset-item-${a.id}`}
      sortField={sortField}
      sortDir={sortDir}
      onSort={onSort}
    />
  );
}
