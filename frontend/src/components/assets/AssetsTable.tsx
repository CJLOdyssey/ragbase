import { useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { DataTable, type DataTableColumn } from '../shared/list';
import { useRowMenu } from '../shared/list/useRowMenu';
import { STATUS_COLORS } from '../shared/statusColors';
import {
  ArrowLeft,
  BookOpen,
  Braces,
  Download,
  FileImage,
  FileSpreadsheet,
  FileText,
  MoreHorizontal,
  Pencil,
  RotateCcw,
  Search,
  Tags,
  Trash2,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import type { IndexProgress } from '../../api/client/assets';
import type { KnowledgeBase } from '../../api/client/knowledgeBases';
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
  onTags?: (asset: AssetItem) => void;
  onDelete: (asset: AssetItem) => void;
  onDownload?: (asset: AssetItem) => void;
  onIndex: (id: string) => void;
  onRetry: (id: string) => void;
  /** 知识库清单 + 归属动作 — 行菜单「分配知识库」子模式使用 */
  kbs?: KnowledgeBase[];
  onAssign?: (assetId: string, kbId: string) => void;
  /** 多选（批量操作）— 传入即渲染 checkbox 列 */
  selectable?: boolean;
  selectedIds?: Set<string>;
  onSelectOne?: (id: string, checked: boolean) => void;
  onSelectAll?: (checked: boolean) => void;
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

/** 知识库归属单元格 — 已分配显示库名，未分配显示警示色「未分类」。 */
function KbCell({
  kbId,
  kbNameById,
}: {
  kbId?: string | null;
  kbNameById: Map<string, string>;
}) {
  const { t } = useTranslation();
  const kbName = kbId ? (kbNameById.get(kbId) ?? kbId) : null;
  return (
    <CellCenter>
      {kbName ? (
        <span
          className="truncate text-[12px] text-[var(--color-text-secondary)]"
          title={kbName}
        >
          {kbName}
        </span>
      ) : (
        <span
          className="text-[12px] text-[var(--color-warning)]"
          title={t('assets.uncategorized.filterChip')}
        >
          {t('assets.uncategorized.filterChip')}
        </span>
      )}
    </CellCenter>
  );
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
  onTags,
  onDelete,
  onDownload,
  onIndex,
  onRetry,
  kbs = [],
  onAssign,
  selectable = false,
  selectedIds,
  onSelectOne,
  onSelectAll,
}: AssetsTableProps) {
  const { t } = useTranslation();
  const menuRef = useRef<HTMLDivElement>(null);

  // Row-menu state machine shared with prompts/admin lists (DIP).
  const menu = useRowMenu({ menuRef });
  const openId = menu.openId;

  // 行菜单子模式：actions（默认）| assign（列出可分配的知识库）。
  // openId 切换即重置，不污染通用 useRowMenu。
  const [assignModeId, setAssignModeId] = useState<string | null>(null);
  const menuMode = openId && assignModeId === openId ? 'assign' : 'actions';
  const resetMenuMode = () => setAssignModeId(null);

  const kbNameById = useMemo(
    () => new Map(kbs.map((k) => [k.id, k.name])),
    [kbs],
  );
  const allSelected =
    selectable && assets.length > 0 && selectedIds !== undefined
      ? assets.every((a) => selectedIds.has(a.id))
      : false;

  const columns: DataTableColumn[] = [];
  if (selectable) {
    columns.push({
      key: 'select',
      header: (
        <input
          type="checkbox"
          aria-label={t('assets.bulk.selectAll')}
          checked={allSelected}
          onChange={(e) => onSelectAll?.(e.target.checked)}
          onClick={(e) => e.stopPropagation()}
          data-testid="select-all"
          className="h-3.5 w-3.5 cursor-pointer accent-[var(--color-accent)]"
        />
      ),
      width: '36px',
      center: true,
    });
  }
  columns.push(
    {
      key: 'name',
      header: t('assets.table.fileName'),
      width: 'minmax(160px,1.5fr)',
      sortable: true,
    },
    {
      key: 'kb',
      header: t('assets.table.kb'),
      width: '110px',
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
  );

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
            title={t('assets.more')}
            hoverVar="--color-accent-soft"
            onClick={() => {
              resetMenuMode();
              menu.toggle(asset.id);
            }}
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
                className="z-50 min-w-[140px] max-h-[320px] overflow-y-auto rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] shadow-xl py-1"
                onClick={(e) => e.stopPropagation()}
              >
                {menuMode === 'actions' ? (
                  <>
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
                      <Download size={12} /> {t('assets.download')}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        menu.close();
                        onTags?.(asset);
                      }}
                      className="w-full text-left px-3 py-1.5 text-sm hover:bg-[var(--color-surface-hover)] flex items-center gap-2"
                      data-testid={`tags-${asset.id}`}
                    >
                      <Tags size={12} /> {t('assets.action.tags')}
                    </button>
                    {onAssign && (
                      <button
                        type="button"
                        disabled={kbs.length === 0}
                        onClick={() => setAssignModeId(asset.id)}
                        className="w-full text-left px-3 py-1.5 text-sm hover:bg-[var(--color-surface-hover)] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        data-testid={`assign-menu-${asset.id}`}
                      >
                        <BookOpen size={12} />{' '}
                        {t('assets.uncategorized.assignAction')}
                      </button>
                    )}
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
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={resetMenuMode}
                      className="w-full text-left px-3 py-1.5 text-xs text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)] flex items-center gap-2 border-b border-[var(--color-border-subtle)] mb-1"
                    >
                      <ArrowLeft size={12} /> {t('assets.uncategorized.back')}
                    </button>
                    {kbs.map((kb) => (
                      <button
                        key={kb.id}
                        type="button"
                        onClick={() => {
                          menu.close();
                          resetMenuMode();
                          onAssign?.(asset.id, kb.id);
                        }}
                        data-testid={`assign-kb-${kb.id}`}
                        className={`w-full text-left px-3 py-1.5 text-sm hover:bg-[var(--color-surface-hover)] flex items-center gap-2 ${
                          asset.knowledgeBaseId === kb.id
                            ? 'text-[var(--color-accent)]'
                            : ''
                        }`}
                      >
                        <BookOpen size={12} /> {kb.name}
                      </button>
                    ))}
                  </>
                )}
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
      case 'select':
        return (
          <CellCenter>
            <input
              type="checkbox"
              aria-label={`${t('assets.bulk.select')} ${asset.name}`}
              checked={selectedIds?.has(asset.id) ?? false}
              onChange={(e) => onSelectOne?.(asset.id, e.target.checked)}
              onClick={(e) => e.stopPropagation()}
              data-testid={`select-${asset.id}`}
              className="h-3.5 w-3.5 cursor-pointer accent-[var(--color-accent)]"
            />
          </CellCenter>
        );
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
      case 'kb':
        return <KbCell kbId={asset.knowledgeBaseId} kbNameById={kbNameById} />;
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
            <StatusPill
              status={status}
              title={
                status === 'failed'
                  ? (asset.indexError ?? undefined)
                  : undefined
              }
            />
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
