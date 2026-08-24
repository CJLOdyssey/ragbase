import { useState } from 'react';
import ConfirmDialog from '../shared/ConfirmDialog';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Modal as AntdModal, Switch } from 'antd';
import { FileText, Pencil, Plus, RotateCcw, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import {
  addAssetChunk,
  deleteAssetChunk,
  listAssetChunks,
  toggleAssetChunk,
  updateAssetChunk,
} from '../../api/client/assets';

interface AssetChunksModalProps {
  asset: AssetItem;
  onClose: () => void;
}

/**
 * Chunk governance panel — view/edit/disable/delete single chunks and append
 * manual ones. Edits re-embed server-side with the KB's bound model.
 */
export default function AssetChunksModal({
  asset,
  onClose,
}: AssetChunksModalProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [draft, setDraft] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const pageSize = 20;

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: ['asset-chunks', asset.id],
    });

  const {
    data: chunks,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['asset-chunks', asset.id],
    queryFn: () => listAssetChunks(asset.id),
  });

  const addMutation = useMutation({
    mutationFn: () => addAssetChunk(asset.id, draft.trim()),
    onSuccess: () => {
      setDraft('');
      void invalidate();
    },
  });
  const editMutation = useMutation({
    mutationFn: (vars: { chunkId: string; text: string }) =>
      updateAssetChunk(asset.id, vars.chunkId, vars.text),
    onSuccess: () => {
      setEditingId(null);
      void invalidate();
    },
  });
  const deleteMutation = useMutation({
    mutationFn: (chunkId: string) => deleteAssetChunk(asset.id, chunkId),
    onSuccess: () => {
      setDeleteTarget(null);
      void invalidate();
    },
  });
  const toggleMutation = useMutation({
    mutationFn: (vars: { chunkId: string; enabled: boolean }) =>
      toggleAssetChunk(asset.id, vars.chunkId, vars.enabled),
    onSuccess: () => void invalidate(),
  });

  const all = chunks ?? [];
  const totalPages = Math.max(1, Math.ceil(all.length / pageSize));
  const pageChunks = all.slice((page - 1) * pageSize, page * pageSize);

  return (
    <AntdModal
      title={`${t('assets.chunks.title')} · ${asset.name}`}
      open={true}
      onCancel={onClose}
      centered
      width={680}
      footer={
        <button
          className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]"
          onClick={onClose}
        >
          {t('common.close')}
        </button>
      }
      styles={{ body: { maxHeight: '65vh', overflowY: 'auto' } }}
    >
      {isLoading ? (
        <div className="py-12 text-center text-sm text-[var(--color-text-muted)]">
          {t('assets.chunks.loading')}
        </div>
      ) : isError ? (
        <div className="py-12 text-center text-sm text-[var(--color-danger)]">
          {t('common.error')}
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-[var(--color-text-muted)] m-0">
            {all.length >= 200
              ? t('assets.chunks.truncated', { count: 200 })
              : t('assets.chunks.count', { count: all.length })}
            {all.length > pageSize ? ` · 第 ${page} / ${totalPages} 页` : ''}
          </p>

          {all.length === 0 && (
            <div className="py-12 text-center">
              <FileText
                size={24}
                className="mx-auto mb-2 text-[var(--color-text-muted)]"
              />
              <p className="text-sm text-[var(--color-text-primary)] m-0">
                {t('assets.chunks.empty')}
              </p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1 m-0">
                {t('assets.chunks.emptyDesc')}
              </p>
            </div>
          )}

          <ul className="flex flex-col gap-2" data-testid="chunk-list">
            {pageChunks.map((chunk, index) => {
              const globalIdx = (page - 1) * pageSize + index;
              const isEditing = editingId === chunk.id;
              const disabledByUser = chunk.enabled === false;
              return (
                <li
                  key={chunk.id ?? `${asset.id}-${globalIdx}`}
                  className={`flex flex-col gap-1 p-3 rounded-lg border bg-[var(--color-surface-raised)] ${
                    disabledByUser
                      ? 'border-dashed border-[var(--color-border)] opacity-60'
                      : 'border-[var(--color-border)]'
                  }`}
                  data-testid={`chunk-${globalIdx}`}
                >
                  <div className="flex items-center gap-2 text-[10px] font-mono text-[var(--color-text-tertiary)]">
                    <span>CHUNK #{globalIdx + 1}</span>
                    {chunk.metadata?.manual === true && (
                      <span>{t('assets.chunks.manualTag')}</span>
                    )}
                    {chunk.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-1.5 py-0.5 rounded bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)]"
                      >
                        {tag}
                      </span>
                    ))}
                    <span className="flex-1" />
                    <Switch
                      size="small"
                      checked={disabledByUser !== true}
                      disabled={!chunk.id || toggleMutation.isPending}
                      onChange={(v) =>
                        toggleMutation.mutate({
                          chunkId: chunk.id!,
                          enabled: v,
                        })
                      }
                      aria-label={t('assets.chunks.toggle')}
                    />
                    <button
                      type="button"
                      aria-label={t('assets.chunks.edit')}
                      title={t('assets.chunks.edit')}
                      disabled={!chunk.id}
                      onClick={() => {
                        setEditingId(chunk.id!);
                        setEditText(chunk.text);
                      }}
                      className="bg-transparent border-none cursor-pointer p-0.5 rounded text-[var(--color-text-muted)] hover:text-[var(--color-accent)] disabled:opacity-40"
                    >
                      <Pencil size={12} />
                    </button>
                    <button
                      type="button"
                      aria-label={t('confirm.delete')}
                      title={t('confirm.delete')}
                      disabled={!chunk.id}
                      onClick={() => setDeleteTarget(chunk.id!)}
                      className="bg-transparent border-none cursor-pointer p-0.5 rounded text-[var(--color-text-muted)] hover:text-[var(--color-danger)] disabled:opacity-40"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>

                  {isEditing ? (
                    <div className="flex flex-col gap-2">
                      <textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        rows={4}
                        className="w-full px-2.5 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)] resize-y font-mono leading-[1.6]"
                      />
                      <div className="flex justify-end gap-1.5">
                        <button
                          type="button"
                          className="px-2.5 py-1 text-xs rounded-md border border-[var(--color-border)] bg-transparent text-[var(--color-text-secondary)] cursor-pointer"
                          onClick={() => setEditingId(null)}
                        >
                          {t('confirm.cancel')}
                        </button>
                        <button
                          type="button"
                          disabled={!editText.trim() || editMutation.isPending}
                          className="px-2.5 py-1 text-xs rounded-md border-none bg-[var(--color-accent)] text-white cursor-pointer disabled:opacity-50"
                          onClick={() =>
                            editMutation.mutate({
                              chunkId: chunk.id!,
                              text: editText.trim(),
                            })
                          }
                        >
                          {t('assets.chunks.save')}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap break-words leading-[1.6] m-0">
                      {chunk.text}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>

          {all.length > pageSize && (
            <div className="flex items-center justify-between pt-2 border-t border-[var(--color-border-subtle)]">
              <span className="text-[11px] font-mono text-[var(--color-text-tertiary)]">
                {page * pageSize - pageSize + 1}-
                {Math.min(page * pageSize, all.length)} / {all.length}
              </span>
              <div className="flex gap-1.5">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded border border-[var(--color-border)] bg-[var(--color-surface-raised)] disabled:opacity-50"
                >
                  <RotateCcw size={11} />
                  上一页
                </button>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="px-2.5 py-1 text-xs rounded border border-[var(--color-border)] bg-[var(--color-surface-raised)] disabled:opacity-50"
                >
                  下一页
                </button>
              </div>
            </div>
          )}

          {/* Manual chunk append */}
          <div className="flex flex-col gap-2 pt-2 mt-1 border-t border-[var(--color-border)]">
            <label className="text-xs font-medium text-[var(--color-text-secondary)] inline-flex items-center gap-1.5">
              <Plus size={12} />
              {t('assets.chunks.addLabel')}
            </label>
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={3}
              placeholder={t('assets.chunks.addPlaceholder')}
              className="w-full px-2.5 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)] resize-y leading-[1.6]"
            />
            <div className="flex justify-end">
              <button
                type="button"
                disabled={!draft.trim() || addMutation.isPending}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md border-none bg-[var(--color-accent)] text-white cursor-pointer disabled:opacity-50"
                onClick={() => addMutation.mutate()}
              >
                <FileText size={12} />
                {addMutation.isPending
                  ? t('assets.chunks.saving')
                  : t('assets.chunks.addButton')}
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteTarget && (
        <ConfirmDialog
          title={t('assets.chunks.deleteTitle')}
          message={t('assets.chunks.deleteConfirm')}
          danger
          onConfirm={() => deleteMutation.mutate(deleteTarget)}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </AntdModal>
  );
}
