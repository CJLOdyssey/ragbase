import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import {
  deleteAsset,
  importUrl,
  indexAsset,
  renameAsset,
  retryIndexAsset,
  uploadAsset,
  type IndexProgress,
} from '../../api/client/assets';
import type { IndexingEntry } from './assetUtils';
import { useToast } from '../../utils/useToast';

const INDEX_POLL_TIMEOUT_MS = 120_000;
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

export function useAssetActions(
  setIndexing: React.Dispatch<React.SetStateAction<IndexingEntry[]>>,
  setProgressMap: React.Dispatch<
    React.SetStateAction<Record<string, IndexProgress>>
  >,
  setRenameTarget: (v: AssetItem | null) => void,
  setDeleteTarget: (v: AssetItem | null) => void,
  setUrlImportOpen: (v: boolean) => void,
  setUrlValue: (v: string) => void,
  setUrlName: (v: string) => void,
  urlValue: string,
  urlName: string,
) {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();

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

  return {
    uploadMutation,
    renameMutation,
    deleteMutation,
    indexMutation,
    retryIndexMutation,
    urlImportMutation,
    validateAndUpload,
  };
}
