import { useMemo, useState } from 'react';
import ConfirmDialog from '../shared/ConfirmDialog';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Database, FileText, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import { listAssets } from '../../api/client/assets';
import {
  assignAssetToKb,
  createKnowledgeBase,
  deleteKnowledgeBase,
  listKnowledgeBases,
  updateKnowledgeBase,
  type KnowledgeBase,
} from '../../api/client/knowledgeBases';
import { listModels, type ModelInfo } from '../../api/client/models';
import KbCard, { KB_ACCENTS } from './KbCard';
import KbNewModal from './KbNewModal';
import KbRecallDrawer from './KbRecallDrawer';
import KbSummaryBar from './KbSummaryBar';
import { useToast } from '../../utils/useToast';

interface FormState {
  mode: 'create' | 'edit';
  kb?: KnowledgeBase;
}

export default function KnowledgeBasePage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FormState | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeBase | null>(null);
  const [testTarget, setTestTarget] = useState<KnowledgeBase | null>(null);

  const { data: kbs = [], isLoading } = useQuery({
    queryKey: ['knowledge-bases'],
    queryFn: listKnowledgeBases,
  });

  const { data: assets = [] } = useQuery({
    queryKey: ['assets'],
    queryFn: listAssets,
  });

  const { data: models = [] } = useQuery({
    queryKey: ['models'],
    queryFn: listModels,
  });

  const createMutation = useMutation({
    mutationFn: ({
      name,
      description,
    }: {
      name: string;
      description: string;
    }) => createKnowledgeBase(name, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      setForm(null);
      toast(t('toast.saveSuccess'), 'success');
    },
    onError: () => toast(t('toast.error'), 'error'),
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      name,
      description,
    }: {
      id: string;
      name: string;
      description: string;
    }) => updateKnowledgeBase(id, name, description),
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
      toast(t('toast.deleteSuccess'), 'success');
    },
    onError: () => toast(t('toast.deleteFailed'), 'error'),
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

  const perKb = useMemo(() => {
    const map = new Map<string, { assetCount: number; indexedCount: number }>();
    for (const a of assets) {
      if (!a.knowledgeBaseId) continue;
      const cur = map.get(a.knowledgeBaseId) ?? {
        assetCount: 0,
        indexedCount: 0,
      };
      cur.assetCount += 1;
      if (a.indexed) cur.indexedCount += 1;
      map.set(a.knowledgeBaseId, cur);
    }
    return map;
  }, [assets]);

  const { totalAssets, indexedRate } = useMemo(() => {
    let total = 0;
    let indexed = 0;
    for (const kb of kbs) {
      const s = perKb.get(kb.id) ?? { assetCount: 0, indexedCount: 0 };
      total += kb.assetCount ?? s.assetCount;
      indexed += s.indexedCount;
    }
    return {
      totalAssets: total,
      indexedRate: total > 0 ? Math.round((indexed / total) * 100) : 0,
    };
  }, [kbs, perKb]);

  const uncategorized = assets.filter(
    (a: AssetItem) =>
      !(a as AssetItem & { knowledgeBaseId?: string }).knowledgeBaseId,
  );

  const handleSave = (name: string, description: string) => {
    if (!name.trim()) return;
    if (form?.mode === 'edit' && form.kb) {
      updateMutation.mutate({ id: form.kb.id, name, description });
    } else {
      createMutation.mutate({ name, description });
    }
  };

  const saving = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="flex h-full flex-col bg-[var(--color-surface)]">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
        <h1 className="m-0 text-lg font-semibold text-[var(--color-text-primary)]">
          {t('kb.title')}
        </h1>
        <button
          className="inline-flex cursor-pointer items-center gap-2 rounded-md border-none bg-[var(--color-accent)] px-3 py-2 text-sm font-medium text-[var(--color-text-on-accent)] hover:opacity-90"
          onClick={() => setForm({ mode: 'create' })}
        >
          <Plus size={16} />
          {t('kb.create')}
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <LoadingState centered={true} />
        ) : kbs.length === 0 ? (
          <EmptyState
            icon={<Database size={24} />}
            title={t('kb.noKbs')}
            description={t('kb.createDesc')}
            centered={true}
          />
        ) : (
          <>
            <div className="mb-6">
              <KbSummaryBar
                totalKbs={kbs.length}
                totalAssets={totalAssets}
                indexedRate={indexedRate}
              />
            </div>

            <div className="grid grid-cols-[repeat(auto-fill,minmax(290px,1fr))] gap-3.5">
              {kbs.map((kb, idx) => {
                const s = perKb.get(kb.id) ?? {
                  assetCount: 0,
                  indexedCount: 0,
                };
                const assetCount = kb.assetCount ?? s.assetCount;
                const indexedCount = s.indexedCount;
                const indexRate =
                  assetCount > 0
                    ? Math.round((indexedCount / assetCount) * 100)
                    : 0;
                return (
                  <KbCard
                    key={kb.id}
                    kb={kb}
                    accent={KB_ACCENTS[idx % KB_ACCENTS.length]}
                    assetCount={assetCount}
                    indexedCount={indexedCount}
                    indexRate={indexRate}
                    onTest={() => setTestTarget(kb)}
                    onRename={() => setForm({ mode: 'edit', kb })}
                    onDelete={() => setDeleteTarget(kb)}
                  />
                );
              })}

              <button
                className="flex min-h-[220px] flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-[var(--color-border)] text-[var(--color-text-muted)] transition-colors hover:border-[color-mix(in_srgb,var(--color-accent)_40%,transparent)] hover:bg-[color-mix(in_srgb,var(--color-accent)_5%,transparent)]"
                onClick={() => setForm({ mode: 'create' })}
              >
                <span className="text-2xl">+</span>
                <span className="text-sm">{t('kb.create')}</span>
              </button>
            </div>
          </>
        )}

        {uncategorized.length > 0 && (
          <section className="mt-8">
            <h2 className="mb-3 text-sm font-medium text-[var(--color-text-secondary)]">
              {t('kb.uncategorized')}
            </h2>
            <div className="flex flex-col gap-2">
              {uncategorized.map((asset: AssetItem) => (
                <div
                  key={asset.id}
                  className="flex items-center gap-3 rounded-lg bg-[var(--color-surface-raised)] px-4 py-2"
                >
                  <FileText
                    size={16}
                    className="shrink-0 text-[var(--color-text-muted)]"
                  />
                  <span className="flex-1 truncate text-sm text-[var(--color-text-primary)]">
                    {asset.name}
                  </span>
                  <select
                    className="cursor-pointer rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 text-xs text-[var(--color-text-primary)] outline-none"
                    value={asset.knowledgeBaseId ?? ''}
                    onChange={(e) => {
                      const kbId = e.target.value || null;
                      assignMutation.mutate({ assetId: asset.id, kbId });
                    }}
                  >
                    <option value="" disabled>
                      {t('kb.assignTo')}
                    </option>
                    {kbs.map((kb) => (
                      <option key={kb.id} value={kb.id}>
                        {kb.name}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>

      {form && (
        <KbNewModal
          open={true}
          mode={form.mode}
          initialName={form.kb?.name ?? ''}
          initialDescription={form.kb?.description ?? ''}
          models={models as ModelInfo[]}
          saving={saving}
          onClose={() => setForm(null)}
          onSave={handleSave}
        />
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

      {testTarget && (
        <KbRecallDrawer
          open={true}
          knowledgeBaseId={testTarget.id}
          knowledgeBaseName={testTarget.name}
          onClose={() => setTestTarget(null)}
        />
      )}
    </div>
  );
}
