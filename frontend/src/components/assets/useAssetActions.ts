import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import {
  deleteAsset,
  downloadAssetFile,
  importUrl,
  indexAsset,
  renameAsset,
  retryIndexAsset,
  setAssetTags,
  uploadAsset,
  type IndexProgress,
} from '../../api/client/assets';
import {
  assignAssetToKb,
  batchAssignAssetsToKb,
} from '../../api/client/knowledgeBases';
import type { IndexingEntry } from './assetUtils';
import { useToast } from '../../utils/useToast';

const INDEX_POLL_TIMEOUT_MS = 120_000;
const IMAGE_TYPES = new Set([
  'image/png',
  'image/jpeg',
  'image/webp',
  'image/gif',
  'image/bmp',
]);
const DOC_TYPES = new Set([
  'application/pdf',
  'text/plain',
  'text/markdown',
  'text/csv',
  'text/html',
  'application/msword',
  'application/vnd.ms-excel',
  'application/vnd.ms-powerpoint',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
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
  /** 批量分配成功后的回调（清空选中集） */
  onBulkAssignDone?: (assignedCount: number, skippedCount: number) => void,
  /** 批量分配目标库名解析 */
  getKbName?: (kbId: string) => string,
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

  // 归属 KB（不触发索引 — 顺序硬约束：先分配再索引，KB 决定向量空间）
  const assignMutation = useMutation({
    mutationFn: ({ assetId, kbId }: { assetId: string; kbId: string }) =>
      assignAssetToKb(assetId, kbId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      toast(t('assets.uncategorized.assignSuccess'), 'success');
    },
    onError: () => toast(t('toast.error'), 'error'),
  });

  const urlImportMutation = useMutation({
    // 提交前统一 trim 并在 hook 侧校验 URL 格式（input type=url 未包在
    // form 中，浏览器校验不触发）；失败给结构化提示而非静默。
    mutationFn: () => {
      const trimmed = urlValue.trim();
      let parsed: URL;
      try {
        parsed = new URL(trimmed);
      } catch {
        throw new Error(t('assets.urlImport.invalidUrl'));
      }
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        throw new Error(t('assets.urlImport.invalidUrl'));
      }
      return importUrl(trimmed, urlName.trim() || undefined);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      setUrlImportOpen(false);
      setUrlValue('');
      setUrlName('');
      toast(t('assets.upload.success'), 'success');
    },
    onError: (err: unknown) => {
      const anyErr = err as {
        response?: { data?: { detail?: string | { message?: string } } };
        message?: string;
      };
      const detail =
        (typeof anyErr?.response?.data?.detail === 'string'
          ? anyErr.response?.data?.detail
          : (anyErr?.response?.data?.detail as { message?: string })
              ?.message) || anyErr?.message;
      // 后端对 Google 私有文档会返回可操作提示，优先展示
      toast(detail || t('assets.urlImport.failed'), 'error');
    },
  });

  const validateAndUpload = (file: File) => {
    let mime = file.type;
    if (!mime || mime === 'application/octet-stream') {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';
      // 图片扩展名兜底：MIME 缺失/octet-stream 的合法图片此前被误拒
      // （DOC_TYPES/IMAGE_TYPES 都允许图片，但 fallback 表漏了图片）。
      const fallback: Record<string, string> = {
        csv: 'text/csv',
        html: 'text/html',
        htm: 'text/html',
        doc: 'application/msword',
        xls: 'application/vnd.ms-excel',
        ppt: 'application/vnd.ms-powerpoint',
        pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        md: 'text/markdown',
        txt: 'text/plain',
        pdf: 'application/pdf',
        docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        png: 'image/png',
        jpg: 'image/jpeg',
        jpeg: 'image/jpeg',
        webp: 'image/webp',
        gif: 'image/gif',
        bmp: 'image/bmp',
      };
      mime = fallback[ext] || mime;
    }
    const allowed = IMAGE_TYPES.has(mime) || DOC_TYPES.has(mime);
    if (!allowed) {
      toast(t('assets.upload.typeDenied', { name: file.name }), 'error');
      return;
    }
    const limit = IMAGE_TYPES.has(mime) ? MAX_IMAGE_BYTES : MAX_DOC_BYTES;
    if (file.size > limit) {
      toast(t('assets.upload.tooLarge', { name: file.name }), 'error');
      return;
    }
    uploadMutation.mutate(file);
  };

  // 批量分配/标签/下载：请求逻辑收敛到 hook（SoC——页面只做编排）。
  const bulkAssignMutation = useMutation({
    mutationFn: (vars: { assetIds: string[]; kbId: string }) =>
      batchAssignAssetsToKb(vars.assetIds, vars.kbId),
    onSuccess: (result, variables) => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      const kbName = getKbName?.(variables.kbId) ?? '';
      toast(
        result.skippedCount > 0
          ? t('assets.bulk.assignPartial', {
              assigned: result.assignedCount,
              skipped: result.skippedCount,
            })
          : t('assets.bulk.assignSuccess', {
              count: result.assignedCount,
              name: kbName,
            }),
        'success',
      );
      onBulkAssignDone?.(result.assignedCount, result.skippedCount);
    },
    onError: () => toast(t('toast.error'), 'error'),
  });

  const setTagsMutation = useMutation({
    mutationFn: (vars: { id: string; tags: string[] }) =>
      setAssetTags(vars.id, vars.tags),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
    onError: () => toast(t('toast.error'), 'error'),
  });

  const handleDownload = async (asset: AssetItem): Promise<void> => {
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

  return {
    uploadMutation,
    renameMutation,
    deleteMutation,
    indexMutation,
    retryIndexMutation,
    assignMutation,
    urlImportMutation,
    bulkAssignMutation,
    setTagsMutation,
    handleDownload,
    validateAndUpload,
  };
}
