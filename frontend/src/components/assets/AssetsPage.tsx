import { useEffect, useRef, useState, type ChangeEvent } from 'react';
import ConfirmDialog from '../shared/ConfirmDialog';
import EmptyState from '../shared/EmptyState';
import Modal from '../shared/Modal';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  FileText,
  FileUp,
  Image as ImageIcon,
  Link,
  RotateCcw,
  Search,
} from 'lucide-react';
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

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function AssetsPage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [renameTarget, setRenameTarget] = useState<AssetItem | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<AssetItem | null>(null);
  const [urlImportOpen, setUrlImportOpen] = useState(false);
  const [urlValue, setUrlValue] = useState('');
  const [urlName, setUrlName] = useState('');
  const [indexing, setIndexing] = useState<
    Array<{ id: string; deadline: number }>
  >([]);
  const [progressMap, setProgressMap] = useState<Record<string, IndexProgress>>({});

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

  // Fetch progress for indexing assets
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

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
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

  const handleRenameConfirm = () => {
    if (renameTarget && renameValue.trim()) {
      renameMutation.mutate({ id: renameTarget.id, name: renameValue.trim() });
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)]">
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)] m-0">
          {t('assets.title')}
        </h1>
        <div className="flex items-center gap-2">
          <button
            className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
            onClick={() => setUrlImportOpen(true)}
          >
            <Link size={16} />
            {t('assets.urlImport.button')}
          </button>
          <button
            className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-accent)] text-white hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadMutation.isPending}
          >
            <FileUp size={16} />
            {uploadMutation.isPending
              ? t('assets.upload.uploading')
              : t('assets.upload.button')}
          </button>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          className="hidden"
          data-testid="asset-file-input"
          onChange={handleFileChange}
        />
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <p className="text-sm text-[var(--color-text-muted)]">
              {t('common.loading')}
            </p>
          </div>
        ) : assets.length === 0 ? (
          <EmptyState
            icon={<FileText size={24} />}
            description={t('assets.list.empty')}
          />
        ) : (
          <ul className="flex flex-col gap-2" data-testid="asset-list">
            {assets.map((asset) => {
              const progress = progressMap[asset.id];
              const isIndexingActive = indexing.some(
                (i) => i.id === asset.id && i.deadline > Date.now(),
              );
              const hasFailed =
                progress?.stage === 'failed' ||
                (!asset.indexed && !!progress);

              return (
                <li
                  key={asset.id}
                  className="flex flex-col gap-1 px-4 py-3 rounded-lg bg-[var(--color-surface-raised)]"
                  data-testid={`asset-item-${asset.id}`}
                >
                  <div className="flex items-center gap-4">
                    {asset.asset_type === 'image' ? (
                      <ImageIcon
                        size={18}
                        className="text-[var(--color-text-muted)] shrink-0"
                      />
                    ) : (
                      <FileText
                        size={18}
                        className="text-[var(--color-text-muted)] shrink-0"
                      />
                    )}
                    <span className="flex-1 min-w-0 text-sm text-[var(--color-text-primary)] truncate">
                      {asset.name}
                    </span>
                    <span className="text-xs text-[var(--color-text-muted)] whitespace-nowrap">
                      {asset.asset_type} · {formatBytes(asset.size_bytes)}
                    </span>
                    {asset.indexed && (
                      <span className="text-xs text-[var(--color-accent)] whitespace-nowrap">
                        indexed
                      </span>
                    )}
                    <div className="flex items-center gap-2 shrink-0">
                      {asset.asset_type === 'document' && !asset.indexed && (
                        <button
                          className="text-xs px-2 py-1 rounded-md cursor-pointer border-none bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                          onClick={() => indexMutation.mutate(asset.id)}
                          disabled={isIndexingActive}
                          data-testid={`index-${asset.id}`}
                        >
                          <Search size={12} className="inline mr-1" />
                          {isIndexingActive
                            ? t('assets.list.indexing')
                            : t('assets.list.index')}
                        </button>
                      )}
                      {hasFailed && (
                        <button
                          className="text-xs px-2 py-1 rounded-md cursor-pointer border-none bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                          onClick={() => retryIndexMutation.mutate(asset.id)}
                          disabled={retryIndexMutation.isPending}
                          data-testid={`retry-${asset.id}`}
                        >
                          <RotateCcw size={12} className="inline mr-1" />
                          {t('assets.list.retry')}
                        </button>
                      )}
                      <button
                        className="text-xs px-2 py-1 rounded-md cursor-pointer border-none bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                        onClick={() => {
                          setRenameTarget(asset);
                          setRenameValue(asset.name);
                        }}
                        data-testid={`rename-${asset.id}`}
                      >
                        {t('assets.list.rename')}
                      </button>
                      <button
                        className="text-xs px-2 py-1 rounded-md cursor-pointer border-none bg-[color-mix(in_srgb,var(--color-danger)_12%,transparent)] text-[var(--color-danger)]"
                        onClick={() => setDeleteTarget(asset)}
                        data-testid={`delete-${asset.id}`}
                      >
                        {t('confirm.delete')}
                      </button>
                    </div>
                  </div>
                  {isIndexingActive && progress && (
                    <div className="flex items-center gap-2 pl-[26px]" data-testid={`progress-${asset.id}`}>
                      <div className="flex-1 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
                        <div
                          className="h-full rounded-full bg-[var(--color-accent)] transition-[width] duration-300"
                          style={{ width: `${Math.min(progress.percentage, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-[var(--color-text-muted)] whitespace-nowrap">
                        {progress.stage ? `${progress.stage} · ` : ''}{progress.percentage}%
                      </span>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {renameTarget && (
        <Modal
          title={t('assets.list.rename')}
          onClose={() => setRenameTarget(null)}
          ariaLabel={t('assets.list.rename')}
          width={420}
          footer={
            <>
              <button
                className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]"
                onClick={() => setRenameTarget(null)}
              >
                {t('confirm.cancel')}
              </button>
              <button
                className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-accent)] text-white hover:opacity-90"
                onClick={handleRenameConfirm}
              >
                {t('confirm.confirm')}
              </button>
            </>
          }
        >
          <input
            type="text"
            className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            data-testid="rename-input"
            aria-label={t('assets.list.rename')}
          />
        </Modal>
      )}

      {deleteTarget && (
        <ConfirmDialog
          title={t('assets.list.rename')}
          message={t('assets.list.deleteConfirm', { name: deleteTarget.name })}
          danger
          onConfirm={() => deleteMutation.mutate(deleteTarget.id)}
          onCancel={() => setDeleteTarget(null)}
        />
      )}

      {urlImportOpen && (
        <Modal
          title={t('assets.urlImport.title')}
          onClose={() => setUrlImportOpen(false)}
          ariaLabel={t('assets.urlImport.title')}
          width={480}
          footer={
            <>
              <button
                className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]"
                onClick={() => setUrlImportOpen(false)}
              >
                {t('confirm.cancel')}
              </button>
              <button
                className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-accent)] text-white hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
                onClick={() => urlImportMutation.mutate()}
                disabled={!urlValue.trim() || urlImportMutation.isPending}
              >
                {urlImportMutation.isPending
                  ? t('assets.urlImport.importing')
                  : t('assets.urlImport.submit')}
              </button>
            </>
          }
        >
          <div className="flex flex-col gap-4 p-6">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[var(--color-text-primary)]">
                {t('assets.urlImport.urlLabel')}
              </label>
              <input
                type="url"
                className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
                placeholder="https://example.com/document.pdf"
                value={urlValue}
                onChange={(e) => setUrlValue(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[var(--color-text-primary)]">
                {t('assets.urlImport.nameLabel')}
              </label>
              <input
                type="text"
                className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
                placeholder={t('assets.urlImport.namePlaceholder')}
                value={urlName}
                onChange={(e) => setUrlName(e.target.value)}
              />
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
