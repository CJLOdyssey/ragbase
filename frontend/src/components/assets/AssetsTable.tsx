import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
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

const GRID = 'minmax(220px,3fr) 84px 92px 116px 110px 132px 150px';

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

const SORT_FIELDS: Record<number, string> = {
  0: 'name',
  1: 'format',
  2: 'size',
  3: 'status',
  4: 'chunks',
  5: 'updated',
};

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
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [menuPos, setMenuPos] = useState<{ top: number; right: number } | null>(
    null,
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const menuRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (menuRef.current && menuRef.current.contains(target)) return;
      if (containerRef.current && containerRef.current.contains(target)) return;
      // also check portal menu is outside container, so check menuRef
      setOpenMenu(null);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);
  const HEADERS = [
    t('assets.table.fileName'),
    t('assets.table.format'),
    t('assets.table.size'),
    t('assets.table.status'),
    t('assets.table.chunks'),
    t('assets.table.updated'),
    t('assets.table.actions'),
  ];
  const renderSort = (idx: number) => {
    const field = SORT_FIELDS[idx];
    if (!field || !onSort) return null;
    const active = sortField === field;
    return (
      <span
        className={`ml-1 text-[10px] ${active ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-tertiary)]'}`}
      >
        {active ? (sortDir === 'asc' ? '↑' : '↓') : '↕'}
      </span>
    );
  };
  return (
    <div
      ref={containerRef}
      className="rounded-[14px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] overflow-visible"
    >
      <div
        className="grid items-center h-10 px-[18px] border-b border-[var(--color-border-subtle)] bg-[color-mix(in_srgb,var(--color-surface-hover)_40%,transparent)]"
        style={{ gridTemplateColumns: GRID }}
      >
        {HEADERS.map((h, i) => (
          <div
            key={`${h}-${i}`}
            onClick={() => {
              const f = SORT_FIELDS[i];
              if (f && onSort) onSort(f);
            }}
            className={`text-[10.5px] font-semibold tracking-[0.07em] uppercase font-mono text-[var(--color-text-tertiary)] flex items-center ${i === HEADERS.length - 1 ? 'justify-center' : ''} ${SORT_FIELDS[i] ? 'cursor-pointer hover:text-[var(--color-text-secondary)]' : ''}`}
          >
            {h}
            {renderSort(i)}
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
              <FileTypeIcon ext={ext} />
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
              <ActionButton
                title={t('assets.action.chunks')}
                hoverVar="--color-accent"
                onClick={() => onChunks(asset)}
                data-testid={`chunks-${asset.id}`}
              >
                <Braces size={12} />
              </ActionButton>
              <div
                className="relative"
                ref={(el) => {
                  if (el) buttonRefs.current.set(asset.id, el);
                  else buttonRefs.current.delete(asset.id);
                }}
              >
                <ActionButton
                  title="更多"
                  hoverVar="--color-accent-soft"
                  onClick={() => {
                    const el = buttonRefs.current.get(asset.id);
                    if (el) {
                      const rect = el.getBoundingClientRect();
                      setMenuPos({
                        top: rect.bottom + 6,
                        right: window.innerWidth - rect.right,
                      });
                    }
                    setOpenMenu(openMenu === asset.id ? null : asset.id);
                  }}
                  data-testid={`more-${asset.id}`}
                >
                  <MoreHorizontal size={12} />
                </ActionButton>
                {openMenu === asset.id &&
                  menuPos &&
                  createPortal(
                    <div
                      ref={menuRef}
                      style={{
                        position: 'fixed',
                        top: menuPos.top,
                        right: menuPos.right,
                      }}
                      className="z-50 min-w-[140px] rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] shadow-xl py-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        type="button"
                        onClick={() => {
                          setOpenMenu(null);
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
                          setOpenMenu(null);
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
                          setOpenMenu(null);
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
        );
      })}
    </div>
  );
}
