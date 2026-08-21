import { useEffect, useRef, useState, type DragEvent } from 'react';
import ConfirmDialog from '../shared/ConfirmDialog';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { useQuery } from '@tanstack/react-query';
import { FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import {
  downloadAssetFile,
  getIndexProgress,
  listAssets,
  type IndexProgress,
} from '../../api/client/assets';
import AssetChunksModal from './AssetChunksModal';
import AssetPreviewDrawer from './AssetPreviewDrawer';
import AssetsGrid from './AssetsGrid';
import AssetsHeader, { type ViewMode } from './AssetsHeader';
import AssetsRenameModal from './AssetsRenameModal';
import AssetsStats from './AssetsStats';
import AssetsTable from './AssetsTable';
import AssetsToolbar from './AssetsToolbar';
import AssetsUrlModal from './AssetsUrlModal';
import { type IndexingEntry } from './assetUtils';
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
    queryFn: listAssets,
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
    uploadMutation,
    renameMutation,
    deleteMutation,
    indexMutation,
    retryIndexMutation,
    urlImportMutation,
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

  const {
    search,
    setSearch,
    formats,
    setFormats,
    statuses,
    setStatuses,
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
  } = useAssetSelection(assets, indexing, progressMap);

  const handleDownload = async (asset: AssetItem) => {
    try {
      await downloadAssetFile(asset.id, asset.name);
      toast(
        t('common.downloadSuccess', { defaultValue: '下载已开始' }),
        'success',
      );
    } catch {
      toast(t('common.downloadFailed', { defaultValue: '下载失败' }), 'error');
    }
  };

  const { bump } = useAssetBump(scrollRef);

  const handlePreview = (asset: AssetItem) => {
    setPreviewTarget(asset);
    bump(asset);
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
        className="flex-1 overflow-y-auto px-8 py-6 min-h-0 relative"
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
          <div className="rounded-[14px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] py-14 px-6 flex flex-col items-center justify-center text-center">
            <EmptyState
              icon={<FileText size={24} />}
              title={t('assets.list.empty')}
              description={t('assets.list.emptyDesc')}
              centered
            />
          </div>
        ) : (
          <div className="flex flex-col gap-5">
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
              timeRange={timeRange}
              onTimeRangeChange={setTimeRange}
              customFrom={customFrom}
              customTo={customTo}
              onCustomTimeChange={(f, to) => {
                setCustomFrom(f);
                setCustomTo(to);
              }}
            />

            {showFilteredEmpty ? (
              <div className="rounded-[14px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] py-12 px-6 flex flex-col items-center justify-center text-center">
                <EmptyState
                  icon={<FileText size={24} />}
                  title="无匹配素材"
                  description="调整搜索或筛选条件"
                  centered
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
                onDelete={setDeleteTarget}
                onDownload={handleDownloadWithBump}
                onIndex={(id) => indexMutation.mutate(id)}
                onRetry={(id) => retryIndexMutation.mutate(id)}
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
                onDelete={setDeleteTarget}
                onDownload={handleDownloadWithBump}
                onIndex={(id) => indexMutation.mutate(id)}
                onRetry={(id) => retryIndexMutation.mutate(id)}
              />
            )}
          </div>
        )}
      </div>

      <AssetsRenameModal
        target={renameTarget}
        value={renameValue}
        onValueChange={setRenameValue}
        onClose={() => setRenameTarget(null)}
        onConfirm={handleRenameConfirm}
      />

      {deleteTarget && (
        <ConfirmDialog
          title={t('assets.list.rename')}
          message={t('assets.list.deleteConfirm', { name: deleteTarget.name })}
          danger
          onConfirm={() => deleteMutation.mutate(deleteTarget.id)}
          onCancel={() => setDeleteTarget(null)}
        />
      )}

      <AssetsUrlModal
        open={urlImportOpen}
        urlValue={urlValue}
        urlName={urlName}
        onUrlChange={setUrlValue}
        onNameChange={setUrlName}
        onClose={() => setUrlImportOpen(false)}
        onSubmit={() => urlImportMutation.mutate()}
        submitting={urlImportMutation.isPending}
      />

      {chunksTarget && (
        <AssetChunksModal
          asset={chunksTarget}
          onClose={() => setChunksTarget(null)}
        />
      )}

      {previewTarget && (
        <AssetPreviewDrawer
          asset={previewTarget}
          indexing={indexing}
          progressMap={progressMap}
          onClose={() => setPreviewTarget(null)}
          onOpenChunks={(a) => {
            setPreviewTarget(null);
            setChunksTarget(a);
          }}
        />
      )}
    </div>
  );
}
