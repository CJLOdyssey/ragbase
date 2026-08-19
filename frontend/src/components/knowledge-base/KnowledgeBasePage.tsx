import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Database, FileText, Plus, Pencil, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import EmptyState from '../shared/EmptyState';
import Modal from '../shared/Modal';
import ConfirmDialog from '../shared/ConfirmDialog';
import {
  listKnowledgeBases,
  createKnowledgeBase,
  updateKnowledgeBase,
  deleteKnowledgeBase,
  type KnowledgeBase,
} from '../../api/client/knowledgeBases';
import { listAssets } from '../../api/client/assets';
import type { AssetItem } from '../../types/assets';
import { assignAssetToKb } from '../../api/client/knowledgeBases';
import { useToast } from '../../utils/useToast';

interface KbFormState {
  mode: 'create' | 'edit';
  kb?: KnowledgeBase;
  name: string;
  description: string;
}

export default function KnowledgeBasePage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<KbFormState | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeBase | null>(null);

  const { data: kbs = [], isLoading } = useQuery({
    queryKey: ['knowledge-bases'],
    queryFn: listKnowledgeBases,
  });

  const { data: assets = [] } = useQuery({
    queryKey: ['assets'],
    queryFn: listAssets,
  });

  const createMutation = useMutation({
    mutationFn: ({ name, description }: { name: string; description: string }) =>
      createKnowledgeBase(name, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      setForm(null);
      toast(t('toast.saveSuccess'), 'success');
    },
    onError: () => toast(t('toast.error'), 'error'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, name, description }: { id: string; name: string; description: string }) =>
      updateKnowledgeBase(id, name, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      setForm(null);
      toast(t('toast.saveSuccess'), 'success');
    },
    onError: () => toast(t('toast.error'), 'error'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteKnowledgeBase(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      setDeleteTarget(null);
      toast(t('toast.saveSuccess'), 'success');
    },
    onError: () => toast(t('toast.error'), 'error'),
  });

  const assignMutation = useMutation({
    mutationFn: ({ assetId, kbId }: { assetId: string; kbId: string | null }) =>
      assignAssetToKb(assetId, kbId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
    },
    onError: () => toast(t('toast.error'), 'error'),
  });

  const uncategorized = assets.filter(
    (a: AssetItem) => !(a as AssetItem & { knowledge_base_id?: string }).knowledge_base_id,
  );

  const handleFormSave = () => {
    if (!form || !form.name.trim()) return;
    if (form.mode === 'create') {
      createMutation.mutate({ name: form.name.trim(), description: form.description.trim() });
    } else if (form.kb) {
      updateMutation.mutate({ id: form.kb.id, name: form.name.trim(), description: form.description.trim() });
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)]">
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)] m-0">
          {t('kb.title')}
        </h1>
        <button
          className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none bg-[var(--color-accent)] text-white hover:opacity-90"
          onClick={() => setForm({ mode: 'create', name: '', description: '' })}
        >
          <Plus size={16} />
          {t('kb.create')}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <p className="text-sm text-[var(--color-text-muted)]">{t('common.loading')}</p>
          </div>
        ) : kbs.length === 0 ? (
          <EmptyState
            icon={<Database size={24} />}
            title={t('kb.noKbs')}
            description={t('kb.createDesc')}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {kbs.map((kb) => (
              <div
                key={kb.id}
                className="flex flex-col gap-2 p-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raised)]"
              >
                <div className="flex items-center gap-2">
                  <Database size={18} className="text-[var(--color-accent)] shrink-0" />
                  <span className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                    {kb.name}
                  </span>
                </div>
                {kb.description && (
                  <p className="text-xs text-[var(--color-text-muted)] m-0 line-clamp-2">
                    {kb.description}
                  </p>
                )}
                <div className="text-xs text-[var(--color-text-muted)]">
                  {kb.asset_count ?? 0} {t('kb.assetCount')}
                </div>
                <div className="flex items-center gap-2 mt-auto pt-2 border-t border-[var(--color-border)]">
                  <button
                    className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-transparent border-none cursor-pointer text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]"
                    onClick={() =>
                      setForm({ mode: 'edit', kb, name: kb.name, description: kb.description })
                    }
                  >
                    <Pencil size={12} />
                    {t('assets.list.rename')}
                  </button>
                  <button
                    className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-transparent border-none cursor-pointer text-[var(--color-danger, #dc2626)] hover:bg-[color-mix(in_srgb,var(--color-danger)_12%,transparent)]"
                    onClick={() => setDeleteTarget(kb)}
                  >
                    <Trash2 size={12} />
                    {t('confirm.delete')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {uncategorized.length > 0 && (
          <section className="mt-8">
            <h2 className="text-sm font-medium text-[var(--color-text-secondary)] mb-3">
              {t('kb.uncategorized')}
            </h2>
            <div className="flex flex-col gap-2">
              {uncategorized.map((asset: AssetItem) => (
                <div
                  key={asset.id}
                  className="flex items-center gap-3 px-4 py-2 rounded-lg bg-[var(--color-surface-raised)]"
                >
                  <FileText size={16} className="text-[var(--color-text-muted)] shrink-0" />
                  <span className="flex-1 text-sm text-[var(--color-text-primary)] truncate">
                    {asset.name}
                  </span>
                  <select
                    className="px-2 py-1 rounded-md text-xs bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none cursor-pointer"
                    defaultValue=""
                    onChange={(e) => {
                      const kbId = e.target.value || null;
                      if (kbId !== null) {
                        assignMutation.mutate({ assetId: asset.id, kbId });
                      }
                    }}
                  >
                    <option value="" disabled>{t('kb.assignTo')}</option>
                    {kbs.map((kb) => (
                      <option key={kb.id} value={kb.id}>{kb.name}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>

      {form && (
        <Modal
          title={form.mode === 'create' ? t('kb.createTitle') : t('kb.editTitle')}
          onClose={() => setForm(null)}
          ariaLabel={form.mode === 'create' ? t('kb.createTitle') : t('kb.editTitle')}
          width={480}
          footer={
            <>
              <button
                className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]"
                onClick={() => setForm(null)}
              >
                {t('confirm.cancel')}
              </button>
              <button
                className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none bg-[var(--color-accent)] text-white hover:opacity-90 disabled:opacity-60"
                onClick={handleFormSave}
                disabled={!form.name.trim() || createMutation.isPending || updateMutation.isPending}
              >
                {t('confirm.confirm')}
              </button>
            </>
          }
        >
          <div className="flex flex-col gap-4 p-6">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[var(--color-text-primary)]">
                {t('kb.name')}
              </label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[var(--color-text-primary)]">
                {t('kb.description')}
              </label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={3}
                className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)] resize-none"
              />
            </div>
          </div>
        </Modal>
      )}

      {deleteTarget && (
        <ConfirmDialog
          title={t('confirm.delete')}
          message={t('kb.deleteConfirm')}
          danger
          onConfirm={() => deleteMutation.mutate(deleteTarget.id)}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
