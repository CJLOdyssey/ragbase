import { useEffect, useRef, useState, type DragEvent } from 'react';
import ConfirmDialog from '../shared/ConfirmDialog';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText, Link, Upload } from 'lucide-react';
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
import AssetsUrlModal from './AssetsUrlModal';
import { computeStats, type IndexingEntry } from './assetUtils';
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

  const stats = computeStats(assets, indexing);
  const showEmpty = !isLoading && assets.length === 0;

  return (
    <div className="flex flex-col h-full bg-[var(--color-surface)]">
      <AssetsHeader
        view={view}
        onViewChange={setView}
        onUrlImport={() => setUrlImportOpen(true)}
        fileInputRef={fileInputRef}
        uploadPending={uploadMutation.isPending}
      />

      <div className="flex-1 overflow-y-auto px-8 py-6 min-h-0">
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
              totalBytes={stats.totalBytes}
            />

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-3.5 rounded-[12px] border-2 border-dashed px-6 py-5 cursor-pointer transition-all"
              style={{
                borderColor: dragging
                  ? 'color-mix(in_srgb, var(--color-accent) 60%, transparent)'
                  : 'var(--color-border)',
                background: dragging
                  ? 'color-mix(in_srgb, var(--color-accent) 6%, transparent)'
                  : 'transparent',
              }}
            >
              <div
                className="w-9 h-9 rounded-[10px] flex items-center justify-center shrink-0"
                style={{
                  color: 'var(--color-accent)',
                  background:
                    'color-mix(in_srgb, var(--color-accent) 10%, transparent)',
                  border:
                    '1px solid color-mix(in_srgb, var(--color-accent) 20%, transparent)',
                }}
              >
                <Upload size={18} />
              </div>
              <div className="min-w-0">
                <div className="text-[13px] font-medium text-[var(--color-text-primary)]">
                  {t('assets.dropHint')}
                </div>
                <div className="text-[12px] text-[var(--color-text-tertiary)] mt-0.5">
                  {t('assets.dropFormats')}
                </div>
              </div>
              <div
                className="ml-auto shrink-0"
                onClick={(e) => {
                  e.stopPropagation();
                  setUrlImportOpen(true);
                }}
              >
                <button
                  type="button"
                  className="inline-flex items-center gap-2 h-9 px-3.5 rounded-[9px] text-[13px] font-medium cursor-pointer border text-[var(--color-text-secondary)] border-[var(--color-border)] bg-[var(--color-surface-raised)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
                >
                  <Link size={15} />
                  {t('assets.urlImport.button')}
                </button>
              </div>
            </div>

            {view === 'table' ? (
              <AssetsTable
                assets={assets}
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
                assets={assets}
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
