import { useEffect, useMemo, useRef, useState, type DragEvent } from 'react';
import ConfirmDialog from '../shared/ConfirmDialog';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import {
  deleteAsset,
  getIndexProgress,
  importUrl,
  indexAsset,
  listAssets,
  renameAsset,
  retryIndexAsset,
  uploadAsset,
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
import { computeStats, type IndexingEntry } from './assetUtils';
import { filterAssets } from './useAssetFilters';
import { useToast } from '../../utils/useToast';

const IMAGE_TYPES = new Set(['image/png', 'image/jpeg', 'image/webp']);
const DOC_TYPES = new Set([
  'application/pdf',
  'text/plain',
  'text/markdown',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
]);
const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const MAX_DOC_BYTES = 20 * 1024 * 1024;
const INDEX_POLL_MS = 3000;
const INDEX_POLL_TIMEOUT_MS = 120_000;

export default function AssetsPage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
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
  const [search, setSearch] = useState('');
  const [formats, setFormats] = useState<string[]>([]);
  const [statuses, setStatuses] = useState<string[]>([]);
  const [timeFrom, setTimeFrom] = useState('');
  const [timeTo, setTimeTo] = useState('');

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

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadAsset(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      toast(t('assets.upload.success'), 'success');
    },
    onError: () => toast(t('assets.upload.failed'), 'error'),
  });

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      renameAsset(id, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      setRenameTarget(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAsset(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      setDeleteTarget(null);
      toast(t('assets.list.deleteSuccess'), 'success');
    },
  });

  const indexMutation = useMutation({
    mutationFn: (id: string) => indexAsset(id),
    onSuccess: (_, id) => {
      setIndexing((prev) => [
        ...prev,
        { id, deadline: Date.now() + INDEX_POLL_TIMEOUT_MS },
      ]);
      setProgressMap((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      toast(t('assets.list.indexSuccess'), 'success');
    },
    onError: () => toast(t('assets.list.documentsOnly'), 'error'),
  });

  const retryIndexMutation = useMutation({
    mutationFn: (id: string) => retryIndexAsset(id),
    onSuccess: (_, id) => {
      setIndexing((prev) => [
        ...prev,
        { id, deadline: Date.now() + INDEX_POLL_TIMEOUT_MS },
      ]);
      setProgressMap((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      toast(t('assets.list.retrySuccess'), 'success');
    },
    onError: () => toast(t('assets.list.retryFailed'), 'error'),
  });

  const urlImportMutation = useMutation({
    mutationFn: () => importUrl(urlValue, urlName || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      setUrlImportOpen(false);
      setUrlValue('');
      setUrlName('');
      toast(t('assets.upload.success'), 'success');
    },
    onError: () => toast(t('assets.urlImport.failed'), 'error'),
  });

  const validateAndUpload = (file: File) => {
    const allowed = IMAGE_TYPES.has(file.type) || DOC_TYPES.has(file.type);
    if (!allowed) {
      toast(t('assets.upload.typeDenied', { name: file.name }), 'error');
      return;
    }
    const limit = IMAGE_TYPES.has(file.type) ? MAX_IMAGE_BYTES : MAX_DOC_BYTES;
    if (file.size > limit) {
      toast(t('assets.upload.tooLarge', { name: file.name }), 'error');
      return;
    }
    uploadMutation.mutate(file);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const files = e.dataTransfer.files;
    for (let i = 0; i < files.length; i += 1) validateAndUpload(files[i]);
  };

  const handleRenameConfirm = () => {
    if (renameTarget && renameValue.trim()) {
      renameMutation.mutate({ id: renameTarget.id, name: renameValue.trim() });
    }
  };

  const stats = useMemo(
    () => computeStats(assets, indexing, progressMap),
    [assets, indexing, progressMap],
  );

  const filteredAssets = useMemo(
    () =>
      filterAssets(assets, {
        search,
        timeFrom: timeFrom ? new Date(timeFrom).getTime() : null,
        timeTo: timeTo ? new Date(timeTo).getTime() : null,
        formats,
        statuses,
        indexing,
        progressMap,
      }),
    [
      assets,
      search,
      timeFrom,
      timeTo,
      formats,
      statuses,
      indexing,
      progressMap,
    ],
  );

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
              timeFrom={timeFrom}
              timeTo={timeTo}
              onTimeChange={(f, to) => {
                setTimeFrom(f);
                setTimeTo(to);
              }}
              formats={formats}
              onFormatsChange={setFormats}
              statuses={statuses}
              onStatusesChange={setStatuses}
              onClear={() => {
                setSearch('');
                setFormats([]);
                setStatuses([]);
                setTimeFrom('');
                setTimeTo('');
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
                assets={filteredAssets}
                indexing={indexing}
                progressMap={progressMap}
                onPreview={setPreviewTarget}
                onChunks={setChunksTarget}
                onRename={(a) => {
                  setRenameTarget(a);
                  setRenameValue(a.name);
                }}
                onDelete={setDeleteTarget}
                onIndex={(id) => indexMutation.mutate(id)}
                onRetry={(id) => retryIndexMutation.mutate(id)}
              />
            ) : (
              <AssetsGrid
                assets={filteredAssets}
                indexing={indexing}
                progressMap={progressMap}
                onPreview={setPreviewTarget}
                onChunks={setChunksTarget}
                onRename={(a) => {
                  setRenameTarget(a);
                  setRenameValue(a.name);
                }}
                onDelete={setDeleteTarget}
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
