import ConfirmDialog from '../shared/ConfirmDialog';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import PromptDetailDrawer from './PromptDetailDrawer';
import PromptEditorModal from './PromptEditorModal';
import PromptGrid from './PromptGrid';
import PromptHeader from './PromptHeader';
import PromptHistoryModal from './PromptHistoryModal';
import PromptTable from './PromptTable';
import PromptTabs from './PromptTabs';
import { usePromptLibrary } from './usePromptLibrary';
import VersionViewModal from './VersionViewModal';

export default function PromptLibraryPage() {
  const {
    filtered,
    counts,
    tab,
    setTab,
    search,
    setSearch,
    view,
    setView,
    isLoading,
    historyPrompt,
    setHistoryPrompt,
    detailPrompt,
    setDetailPrompt,
    versions,
    dialog,
    setDialog,
    handleSave,
    handleRollback,
    deleteMutation,
    isSaving,
    saveError,
  } = usePromptLibrary();

  const showEmpty = !isLoading && filtered.length === 0;
  const hasData = filtered.length > 0;

  return (
    <div className="flex flex-col h-full bg-[var(--color-surface)]">
      <PromptHeader
        search={search}
        onSearchChange={setSearch}
        view={view}
        onViewChange={setView}
        onNew={() => setDialog({ type: 'new' })}
      />

      <div className="flex-1 overflow-y-auto px-8 py-6">
        <PromptTabs tab={tab} onChange={setTab} counts={counts} />

        {isLoading ? (
          <LoadingState centered />
        ) : showEmpty ? (
          <EmptyCard tab={tab} />
        ) : hasData ? (
          view === 'table' ? (
            <PromptTable
              prompts={filtered}
              onEdit={(row) => setDialog({ type: 'edit', row })}
              onDelete={(row) => setDialog({ type: 'delete', row })}
              onHistory={setHistoryPrompt}
              onSelect={setDetailPrompt}
            />
          ) : (
            <PromptGrid prompts={filtered} onSelect={setDetailPrompt} />
          )
        ) : null}
      </div>

      <DialogLayer
        dialog={dialog}
        isSaving={isSaving}
        saveError={saveError}
        onSave={handleSave}
        onDelete={(id) => deleteMutation.mutate(id)}
        onRollback={handleRollback}
        onClose={() => setDialog(null)}
      />

      {detailPrompt && (
        <PromptDetailDrawer
          prompt={detailPrompt}
          onClose={() => setDetailPrompt(null)}
        />
      )}

      {historyPrompt && (
        <PromptHistoryModal
          prompt={historyPrompt}
          versions={versions}
          onClose={() => setHistoryPrompt(null)}
          onView={(v) => setDialog({ type: 'version-view', version: v })}
          onRollback={(v) => {
            handleRollback(v);
            setHistoryPrompt(null);
          }}
        />
      )}
    </div>
  );
}

function EmptyCard({ tab }: { tab: string }) {
  const { t } = useTranslation();
  const isFiltered = tab !== 'all';
  if (isFiltered) {
    const label =
      tab === 'published' ? '已发布' : tab === 'draft' ? '草稿' : tab;
    return (
      <div className="rounded-[14px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] py-10 px-6 text-center text-[13px] text-[var(--color-text-muted)]">
        暂无{label}数据
      </div>
    );
  }
  return (
    <div className="rounded-[14px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] py-14 px-6 flex flex-col items-center justify-center text-center">
      <EmptyState
        icon={<FileText size={24} />}
        title={t('prompts.list.empty')}
        description={t('prompts.list.emptyDesc')}
        centered
      />
    </div>
  );
}

function DialogLayer({
  dialog,
  isSaving,
  saveError,
  onSave,
  onDelete,
  onRollback,
  onClose,
}: {
  dialog: ReturnType<typeof usePromptLibrary>['dialog'];
  isSaving: boolean;
  saveError: string | null;
  onSave: ReturnType<typeof usePromptLibrary>['handleSave'];
  onDelete: (id: string) => void;
  onRollback: ReturnType<typeof usePromptLibrary>['handleRollback'];
  onClose: () => void;
}) {
  const { t } = useTranslation();
  if (!dialog) return null;
  if (dialog.type === 'new' || dialog.type === 'edit') {
    return (
      <PromptEditorModal
        mode={dialog.type}
        initial={dialog.row ?? null}
        onSave={onSave}
        onClose={onClose}
        saving={isSaving}
        error={saveError}
      />
    );
  }
  if (dialog.type === 'delete' && dialog.row) {
    return (
      <ConfirmDialog
        title={t('prompts.deleteTitle')}
        message={t('prompts.deleteConfirm', { name: dialog.row.name })}
        danger
        confirmLabel={t('confirm.delete')}
        onConfirm={() => onDelete(dialog.row!.id)}
        onCancel={onClose}
      />
    );
  }
  if (dialog.type === 'version-view' && dialog.version) {
    return (
      <VersionViewModal
        version={dialog.version}
        onRollback={() => {
          onRollback(dialog.version!);
          onClose();
        }}
        onClose={onClose}
      />
    );
  }
  return null;
}
