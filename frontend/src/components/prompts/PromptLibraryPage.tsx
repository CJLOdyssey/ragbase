import ConfirmDialog from '../shared/ConfirmDialog';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { PromptItem } from '../../api/client/prompts';
import type { VersionItem } from '../../api/client/versions';
import PromptDetailModal from './PromptDetailModal';
import PromptEditorModal from './PromptEditorModal';
import PromptGrid from './PromptGrid';
import PromptHeader from './PromptHeader';
import PromptHistoryModal from './PromptHistoryModal';
import PromptTable from './PromptTable';
import PromptTabs from './PromptTabs';
import {
  usePromptLibrary,
  type DialogState,
  type PromptSavePayload,
} from './usePromptLibrary';
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
    selectedPrompt,
    openDetail,
    closeDetail,
    versions,
    dialog,
    setDialog,
    handleCreate,
    handleUpdate,
    handleRollback,
    prompts,
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
              onEdit={(row) => setDialog({ type: 'edit', id: row.id })}
              onDelete={(row) => setDialog({ type: 'delete', id: row.id })}
              onHistory={setHistoryPrompt}
              onSelect={openDetail}
            />
          ) : (
            <PromptGrid
              prompts={filtered}
              onSelect={openDetail}
              onEdit={(row) => setDialog({ type: 'edit', id: row.id })}
              onDelete={(row) => setDialog({ type: 'delete', id: row.id })}
              onHistory={setHistoryPrompt}
            />
          )
        ) : null}
      </div>

      {/* 弹窗按 DOM 顺序层叠（后者在上）：详情 < 历史 < DialogLayer(编辑等) */}
      {selectedPrompt && (
        <PromptDetailModal prompt={selectedPrompt} onClose={closeDetail} />
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

      <DialogLayer
        dialog={dialog}
        resolvePrompt={(id) => prompts.find((p) => p.id === id) ?? null}
        isSaving={isSaving}
        saveError={saveError}
        onCreate={handleCreate}
        onUpdate={handleUpdate}
        onDelete={(id) => deleteMutation.mutate(id)}
        onRollback={handleRollback}
        onClose={() => setDialog(null)}
      />
    </div>
  );
}

function EmptyCard({ tab }: { tab: string }) {
  const { t } = useTranslation();
  const isFiltered = tab !== 'all';
  if (isFiltered) {
    const label = tab === 'published' ? '启用' : tab === 'draft' ? '草稿' : tab;
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
  resolvePrompt,
  isSaving,
  saveError,
  onCreate,
  onUpdate,
  onDelete,
  onRollback,
  onClose,
}: {
  dialog: DialogState | null;
  resolvePrompt: (id: string) => PromptItem | null;
  isSaving: boolean;
  saveError: string | null;
  onCreate: (payload: PromptSavePayload) => void;
  onUpdate: (id: string, payload: PromptSavePayload) => void;
  onDelete: (id: string) => void;
  onRollback: (v: VersionItem) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  if (!dialog) return null;

  if (dialog.type === 'new' || dialog.type === 'edit') {
    const initial = dialog.type === 'edit' ? resolvePrompt(dialog.id) : null;
    if (dialog.type === 'edit' && !initial) return null;
    return (
      <PromptEditorModal
        mode={dialog.type}
        initial={initial}
        onSave={(payload) =>
          dialog.type === 'edit'
            ? onUpdate(dialog.id, payload)
            : onCreate(payload)
        }
        onClose={onClose}
        saving={isSaving}
        error={saveError}
      />
    );
  }

  if (dialog.type === 'delete') {
    const { id } = dialog;
    const row = resolvePrompt(id);
    if (!row) return null;
    return (
      <ConfirmDialog
        title={t('prompts.deleteTitle')}
        message={t('prompts.deleteConfirm', { name: row.name })}
        danger
        confirmLabel={t('confirm.delete')}
        onConfirm={() => onDelete(id)}
        onCancel={onClose}
      />
    );
  }

  return (
    <VersionViewModal
      version={dialog.version}
      onRollback={() => {
        onRollback(dialog.version);
        onClose();
      }}
      onClose={onClose}
    />
  );
}
