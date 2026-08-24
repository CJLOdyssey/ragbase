import { useMemo, useState } from 'react';
import ConfirmDialog from '../shared/ConfirmDialog';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { useQuery } from '@tanstack/react-query';
import { Database, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import { listAssets } from '../../api/client/assets';
import {
  listKnowledgeBases,
  type KnowledgeBase,
  type ParserConfigForm,
} from '../../api/client/knowledgeBases';
import { listModels, type ModelInfo } from '../../api/client/models';
import KbCardGrid from './KbCardGrid';
import KbNewModal from './KbNewModal';
import KbRecallModal from './KbRecallModal';
import { computePerKb, computeTotals } from './kbStats';
import KbSummaryBar from './KbSummaryBar';
import UncategorizedSection from './UncategorizedSection';
import { useKbMutations } from './useKbMutations';

interface FormState {
  mode: 'create' | 'edit';
  kb?: KnowledgeBase;
}

export default function KnowledgeBasePage() {
  const { t } = useTranslation();
  const [form, setForm] = useState<FormState | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeBase | null>(null);
  const [testTarget, setTestTarget] = useState<KnowledgeBase | null>(null);

  const closeForm = () => setForm(null);
  const closeDelete = () => setDeleteTarget(null);

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
    // Only needed by the create/edit modal — skip the fetch entirely otherwise.
    enabled: form !== null,
  });

  const { createMutation, updateMutation, deleteMutation, assignMutation } =
    useKbMutations({ closeForm, closeDelete });

  const perKb = useMemo(() => computePerKb(assets), [assets]);
  const { totalAssets, indexedRate } = useMemo(
    () => computeTotals(kbs, perKb),
    [kbs, perKb],
  );

  const uncategorized = assets.filter((a: AssetItem) => !a.knowledgeBaseId);

  const handleSave = (
    name: string,
    description: string,
    embedModel: string,
    parserConfig: ParserConfigForm,
  ) => {
    if (!name.trim() || !embedModel) return;
    if (form?.mode === 'edit' && form.kb) {
      updateMutation.mutate({
        id: form.kb.id,
        name,
        description,
        embedModel,
        parserConfig,
      });
    } else {
      createMutation.mutate({ name, description, embedModel, parserConfig });
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

            <KbCardGrid
              kbs={kbs}
              perKb={perKb}
              onCreate={() => setForm({ mode: 'create' })}
              onTest={setTestTarget}
              onRename={(kb) => setForm({ mode: 'edit', kb })}
              onDelete={setDeleteTarget}
            />
          </>
        )}

        {uncategorized.length > 0 && (
          <UncategorizedSection
            assets={uncategorized}
            kbs={kbs}
            onAssign={(assetId, kbId) =>
              assignMutation.mutate({ assetId, kbId })
            }
          />
        )}
      </div>

      {form && (
        <KbNewModal
          open={true}
          mode={form.mode}
          kb={form.kb ?? null}
          indexedCount={
            form.kb ? (perKb.get(form.kb.id)?.indexedCount ?? 0) : 0
          }
          models={models as ModelInfo[]}
          saving={saving}
          onClose={closeForm}
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
        <KbRecallModal
          open={true}
          knowledgeBaseId={testTarget.id}
          knowledgeBaseName={testTarget.name}
          onClose={() => setTestTarget(null)}
        />
      )}
    </div>
  );
}
