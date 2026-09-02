import { useEffect, useMemo, useRef, useState, type DragEvent } from 'react';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { useQuery } from '@tanstack/react-query';
import { FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import {
  getIndexProgress,
  listAssets,
  type IndexProgress,
} from '../../api/client/assets';
import { listKnowledgeBases } from '../../api/client/knowledgeBases';
import AssetsBulkBar from './AssetsBulkBar';
import AssetsDialogs from './AssetsDialogs';
import AssetsGrid from './AssetsGrid';
import AssetsHeader, { type ViewMode } from './AssetsHeader';
import AssetsStats from './AssetsStats';
import AssetsTable from './AssetsTable';
import AssetsToolbar from './AssetsToolbar';
import AssetsUncategorizedBanner from './AssetsUncategorizedBanner';
import { type IndexingEntry } from './assetUtils';
import KbFilterChip from './KbFilterChip';
import { useAssetActions } from './useAssetActions';
import { useAssetBump } from './useAssetBump';
import { useAssetSelection } from './useAssetSelection';
import { useToast } from '../../utils/useToast';

const INDEX_POLL_MS = 3000;

export default function AssetsPage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [view, setView] = useState<ViewMode>('table');
  const [dragging, setDragging] = useState(false);
  const [renameTarget, setRenameTarget] = useState<AssetItem | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<AssetItem | null>(null);
  const [chunksTarget, setChunksTarget] = useState<AssetItem | null>(null);
  const [previewTarget, setPreviewTarget] = useState<AssetItem | null>(null);
  const [urlImportOpen, setUrlImportOpen] = useState(false);
  const [urlValue, setUrlValue] = useState('');
  const [urlName, setUrlName] = useState('');
  const [indexing, setIndexing] = useState<IndexingEntry[]>([]);
  const [progressMap, setProgressMap] = useState<Record<string, IndexProgress>>(
    {},
  );

  const { data: assets = [], isLoading } = useQuery({
    queryKey: ['assets'],
    queryFn: () => listAssets(),
    refetchInterval: (query) => {
      const now = Date.now();
      const live = indexing.filter((i) => i.deadline > now);
      if (live.length === 0) return false;
      const list = query.state.data as AssetItem[] | undefined;
      const pending = list?.some((a) =>
        live.some((i) => i.id === a.id && !a.indexed),
      );
      return pending ? INDEX_POLL_MS : false;
    },
  });

  // 未分类面板的库选项 — 与知识库页共享同一缓存键
  const { data: kbs = [] } = useQuery({
    queryKey: ['knowledge-bases'],
    queryFn: listKnowledgeBases,
  });

  useEffect(() => {
    const liveIndexing = indexing.filter((i) => i.deadline > Date.now());
    if (liveIndexing.length === 0) return;

    const fetchProgress = async () => {
      const updates: Record<string, IndexProgress> = {};
      for (const { id } of liveIndexing) {
        try {
          const progress = await getIndexProgress(id);
          updates[id] = progress;
        } catch {
          // Ignore errors
        }
      }
      setProgressMap((prev) => ({ ...prev, ...updates }));
    };

    fetchProgress();
    const interval = setInterval(fetchProgress, INDEX_POLL_MS);
    return () => clearInterval(interval);
  }, [indexing]);

  const {
    search,
    setSearch,
    formats,
    setFormats,
    statuses,
    setStatuses,
    kbFilter,
    setKbFilter,
    timeRange,
    setTimeRange,
    customFrom,
    setCustomFrom,
    customTo,
    setCustomTo,
    sortField,
    sortDir,
    stats,
    filteredAssets,
    sortedAssets,
    handleSort,
    selectedIds,
    setSelectedIds,
    handleSelectAll,
    handleSelectOne,
  } = useAssetSelection(assets, indexing, progressMap);

  const {
    uploadMutation,
    renameMutation,
    deleteMutation,
    indexMutation,
    retryIndexMutation,
    assignMutation,
    urlImportMutation,
    bulkAssignMutation,
    setTagsMutation,
    handleDownload: handleDownloadAsset,
    validateAndUpload,
  } = useAssetActions(
    setIndexing,
    setProgressMap,
    setRenameTarget,
    setDeleteTarget,
    setUrlImportOpen,
    setUrlValue,
    setUrlName,
    urlValue,
    urlName,
    (assignedCount, skippedCount) => {
      void assignedCount;
      void skippedCount;
      setSelectedIds(new Set());
    },
    (kbId) => kbs.find((k) => k.id === kbId)?.name ?? '',
  );

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const files = e.dataTransfer.files;
    for (let i = 0; i < files.length; i += 1) validateAndUpload(files[i]);
  };

  const handleRenameConfirm = () => {
    if (!renameTarget) return;
    const rawBase = renameValue.trim();
    if (!rawBase) return;
    // 仅允许 basename，禁止路径与扩展名篡改
    if (rawBase.includes('/') || rawBase.includes('\\')) return;
    const sanitizedBase = rawBase.split('.')[0] || rawBase;
    const idx = renameTarget.name.lastIndexOf('.');
    const ext = idx > 0 ? renameTarget.name.slice(idx) : '';
    const fullName = (sanitizedBase + ext).slice(0, 256);
    renameMutation.mutate({ id: renameTarget.id, name: fullName });
  };

  // 知识库筛选态：'all' | 'unassigned' | <kbId>（banner「立即处理」与工具栏下拉共用）
  const uncategorizedCount = useMemo(
    () => assets.filter((a) => !a.knowledgeBaseId).length,
    [assets],
  );

  // ── 批量操作（分配知识库 / 建立索引）──────────────────────────────
  const selectedList = useMemo(
    () => assets.filter((a) => selectedIds.has(a.id)),
    [assets, selectedIds],
  );
  const canBulkIndex = useMemo(
    () => selectedList.some((a) => a.assetType === 'document' && !a.indexed),
    [selectedList],
  );

  const handleBulkIndex = () => {
    const targets = selectedList.filter(
      (a) => a.assetType === 'document' && !a.indexed,
    );
    if (targets.length === 0) return;
    for (const a of targets) indexMutation.mutate(a.id);
    toast(t('assets.bulk.indexQueued', { count: targets.length }), 'success');
    setSelectedIds(new Set());
  };

  const handleDownload = async (asset: AssetItem) => {
    // 下载逻辑收敛到 useAssetActions（SoC）
    await handleDownloadAsset(asset);
  };

  const { bump } = useAssetBump(scrollRef);

  const handlePreview = (asset: AssetItem) => {
    setPreviewTarget(asset);
    bump(asset);
  };

  const [tagTarget, setTagTarget] = useState<AssetItem | null>(null);
  // setTagsMutation 收敛到 useAssetActions；关闭弹窗是页面编排职责，
  // 通过 mutate(vars, { onSuccess }) 注入而非复制请求逻辑。
  const handleTagsSave = (id: string, tags: string[]) => {
    setTagsMutation.mutate(
      { id, tags },
      { onSuccess: () => setTagTarget(null) },
    );
  };

  const handleChunks = (asset: AssetItem) => {
    setChunksTarget(asset);
    bump(asset);
  };

  const handleDownloadWithBump = async (asset: AssetItem) => {
    bump(asset);
    await handleDownload(asset);
  };

  const showEmpty = !isLoading && assets.length === 0;
  const showFilteredEmpty =
    !isLoading && assets.length > 0 && filteredAssets.length === 0;

  return (
    <div className="flex flex-col h-full bg-[var(--color-surface)]">
      <AssetsHeader
        view={view}
        onViewChange={setView}
        onUrlImport={() => setUrlImportOpen(true)}
        fileInputRef={fileInputRef}
        uploadPending={uploadMutation.isPending}
        onFileSelect={validateAndUpload}
      />

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 min-h-0 relative"
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        {dragging && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-[color-mix(in_srgb,var(--color-accent)_8%,transparent)] border-2 border-dashed border-[var(--color-accent)] rounded-[12px] pointer-events-none m-6">
            <span className="text-sm font-bold text-[var(--color-accent)]">
              松手上传素材
            </span>
          </div>
        )}
        {isLoading ? (
          <LoadingState centered />
        ) : showEmpty ? (
          <div className="rounded-[14px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] min-h-[50vh] px-6 flex flex-col items-center justify-center text-center">
            <EmptyState
              icon={<FileText size={24} />}
              title={t('assets.list.empty')}
              description={t('assets.list.emptyDesc')}
            />
          </div>
        ) : (
          <div className="flex flex-col gap-5">
            <AssetsUncategorizedBanner
              count={uncategorizedCount}
              onHandle={() => {
                setView('table');
                setKbFilter('unassigned');
              }}
            />

            {kbFilter !== 'all' && (
              <KbFilterChip
                kbFilter={kbFilter}
                kbName={kbs.find((k) => k.id === kbFilter)?.name}
                onClear={() => setKbFilter('all')}
              />
            )}

            <AssetsStats
              total={stats.total}
              indexed={stats.indexed}
              processing={stats.processing}
              failed={stats.failed}
              totalBytes={stats.totalBytes}
              filteredCount={filteredAssets.length}
            />

            <AssetsToolbar
              search={search}
              onSearch={setSearch}
              formats={formats}
              onFormatsChange={setFormats}
              statuses={statuses}
              onStatusesChange={setStatuses}
              kbFilter={kbFilter}
              onKbFilterChange={setKbFilter}
              kbs={kbs}
              timeRange={timeRange}
              onTimeRangeChange={setTimeRange}
              customFrom={customFrom}
              customTo={customTo}
              onCustomTimeChange={(f, to) => {
                setCustomFrom(f);
                setCustomTo(to);
              }}
            />

            {selectedIds.size > 0 && (
              <AssetsBulkBar
                count={selectedIds.size}
                kbs={kbs}
                assigning={bulkAssignMutation.isPending}
                indexing={indexMutation.isPending}
                canIndex={canBulkIndex}
                onAssign={(kbId) =>
                  bulkAssignMutation.mutate({
                    assetIds: [...selectedIds],
                    kbId,
                  })
                }
                onIndex={handleBulkIndex}
                onCancel={() => setSelectedIds(new Set())}
              />
            )}

            {showFilteredEmpty ? (
              <div className="rounded-[14px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] min-h-[50vh] px-6 flex flex-col items-center justify-center text-center">
                <EmptyState
                  icon={<FileText size={24} />}
                  title={t('assets.noMatch')}
                  description={t('assets.noMatchDesc')}
                />
              </div>
            ) : view === 'table' ? (
              <AssetsTable
                assets={sortedAssets}
                indexing={indexing}
                progressMap={progressMap}
                sortField={sortField}
                sortDir={sortDir}
                onSort={handleSort}
                onPreview={handlePreview}
                onChunks={handleChunks}
                onRename={(a) => {
                  setRenameTarget(a);
                  const idx = a.name.lastIndexOf('.');
                  setRenameValue(idx > 0 ? a.name.slice(0, idx) : a.name);
                }}
                onTags={setTagTarget}
                onDelete={setDeleteTarget}
                onDownload={handleDownloadWithBump}
                onIndex={(id) => indexMutation.mutate(id)}
                onRetry={(id) => retryIndexMutation.mutate(id)}
                kbs={kbs}
                onAssign={(assetId, kbId) =>
                  assignMutation.mutate({ assetId, kbId })
                }
                selectable={true}
                selectedIds={selectedIds}
                onSelectOne={handleSelectOne}
                onSelectAll={handleSelectAll}
              />
            ) : (
              <AssetsGrid
                assets={sortedAssets}
                indexing={indexing}
                progressMap={progressMap}
                onPreview={handlePreview}
                onChunks={handleChunks}
                onRename={(a) => {
                  setRenameTarget(a);
                  const idx = a.name.lastIndexOf('.');
                  setRenameValue(idx > 0 ? a.name.slice(0, idx) : a.name);
                }}
                onTags={setTagTarget}
                onDelete={setDeleteTarget}
                onDownload={handleDownloadWithBump}
                onIndex={(id) => indexMutation.mutate(id)}
                onRetry={(id) => retryIndexMutation.mutate(id)}
              />
            )}
          </div>
        )}
      </div>

      <AssetsDialogs
        tagTarget={tagTarget}
        onTagsClose={() => setTagTarget(null)}
        onTagsSave={handleTagsSave}
        tagsSaving={setTagsMutation.isPending}
        renameTarget={renameTarget}
        renameValue={renameValue}
        onRenameValueChange={setRenameValue}
        onRenameClose={() => setRenameTarget(null)}
        onRenameConfirm={handleRenameConfirm}
        deleteTarget={deleteTarget}
        onDeleteConfirm={() =>
          deleteTarget && deleteMutation.mutate(deleteTarget.id)
        }
        onDeleteCancel={() => setDeleteTarget(null)}
        urlOpen={urlImportOpen}
        urlValue={urlValue}
        urlName={urlName}
        onUrlChange={setUrlValue}
        onUrlNameChange={setUrlName}
        onUrlClose={() => setUrlImportOpen(false)}
        onUrlSubmit={() => urlImportMutation.mutate()}
        urlSubmitting={urlImportMutation.isPending}
        chunksTarget={chunksTarget}
        onChunksClose={() => setChunksTarget(null)}
        previewTarget={previewTarget}
        indexing={indexing}
        progressMap={progressMap}
        onPreviewClose={() => setPreviewTarget(null)}
        onPreviewChunks={(a) => {
          setPreviewTarget(null);
          setChunksTarget(a);
        }}
      />
    </div>
  );
}
