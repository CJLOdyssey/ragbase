import { useState } from 'react';
import ConfirmDialog from '../shared/ConfirmDialog';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText, History } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  createPrompt,
  deletePrompt,
  listPrompts,
  updatePrompt,
  type PromptItem,
} from '../../api/client/prompts';
import { listVersions, type VersionItem } from '../../api/client/versions';
import PromptEditorModal from './PromptEditorModal';
import PromptListTab from './PromptListTab';
import VersionHistoryTab from './VersionHistoryTab';
import VersionViewModal from './VersionViewModal';
import { useToast } from '../../utils/useToast';

type TabKey = 'list' | 'versions';

interface DialogState {
  type: 'new' | 'edit' | 'delete' | 'version-view';
  row?: PromptItem;
  version?: VersionItem;
}

interface DialogLayerProps {
  dialog: DialogState | null;
  isSaving: boolean;
  saveError: string | null;
  onSave: (payload: Parameters<typeof createPrompt>[0]) => void;
  onDelete: (id: string) => void;
  onRollback: (v: VersionItem) => void;
  onClose: () => void;
}

function DialogLayer({
  dialog,
  isSaving,
  saveError,
  onSave,
  onDelete,
  onRollback,
  onClose,
}: DialogLayerProps) {
  const { t } = useTranslation();

  if (dialog?.type === 'new' || dialog?.type === 'edit') {
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

  if (dialog?.type === 'delete' && dialog.row) {
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

  if (dialog?.type === 'version-view' && dialog.version) {
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

export default function PromptLibraryPage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<TabKey>('list');
  const [selectedPromptId, setSelectedPromptId] = useState<string | null>(null);
  const [dialog, setDialog] = useState<DialogState | null>(null);

  const { data: prompts = [], isLoading: promptsLoading } = useQuery({
    queryKey: ['prompts'],
    queryFn: listPrompts,
  });

  const { data: versions = [], isLoading: versionsLoading } = useQuery({
    queryKey: ['versions', selectedPromptId],
    queryFn: () => listVersions('prompt', selectedPromptId!),
    enabled: activeTab === 'versions' && selectedPromptId !== null,
  });

  const createMutation = useMutation({
    mutationFn: createPrompt,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
      setDialog(null);
      toast(t('prompts.editor.saveHint'), 'success');
    },
    onError: () => toast(t('prompts.editor.saveFailed'), 'error'),
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: Parameters<typeof updatePrompt>[1];
    }) => updatePrompt(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
      setDialog(null);
      toast(t('toast.saveSuccess'), 'success');
    },
    onError: () => toast(t('prompts.editor.saveFailed'), 'error'),
  });

  const deleteMutation = useMutation({
    mutationFn: deletePrompt,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
      setDialog(null);
      toast(t('toast.saveSuccess'), 'success');
    },
    onError: () => toast(t('toast.error'), 'error'),
  });

  const handleNew = () => setDialog({ type: 'new' });

  const handleEdit = (row: PromptItem) => setDialog({ type: 'edit', row });

  const handleDelete = (row: PromptItem) => setDialog({ type: 'delete', row });

  const handleHistory = (row: PromptItem) => {
    setSelectedPromptId(row.id);
    setActiveTab('versions');
  };

  const handleBackToList = () => {
    setActiveTab('list');
    setSelectedPromptId(null);
  };

  const handleViewVersion = (v: VersionItem) =>
    setDialog({ type: 'version-view', version: v });

  const handleRollback = (v: VersionItem) => {
    if (!selectedPromptId) return;
    const snap = v.snapshot as Record<string, string>;
    updateMutation.mutate({
      id: selectedPromptId,
      payload: {
        name: snap.name ?? '',
        category: snap.category ?? 'user',
        content: snap.content ?? '',
      },
    });
  };

  const handleSave = (payload: Parameters<typeof createPrompt>[0]) => {
    if (dialog?.type === 'new') {
      createMutation.mutate(payload);
    } else if (dialog?.type === 'edit' && dialog.row) {
      updateMutation.mutate({ id: dialog.row.id, payload });
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const saveError =
    createMutation.isError || updateMutation.isError
      ? t('prompts.editor.saveFailed')
      : null;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)]">
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)] m-0">
          {t('prompts.title')}
        </h1>
        {activeTab === 'list' && (
          <button
            className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-accent)] text-white hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
            onClick={handleNew}
          >
            {t('prompts.editor.new')}
          </button>
        )}
      </div>

      {/* Body: sidebar + content */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Sidebar tabs */}
        <div className="w-[160px] px-4 py-5 flex flex-col gap-1 shrink-0 border-r border-[var(--color-border)]">
          {(
            [
              ['list', FileText, t('prompts.tab.list')],
              ['versions', History, t('prompts.tab.version')],
            ] as const
          ).map(([tab, Icon, label]) => (
            <button
              key={tab}
              className={`flex items-center gap-3 p-2 px-3 bg-transparent border-none rounded-md text-[var(--color-text-secondary)] text-sm cursor-pointer transition-[background,color] duration-150 text-left hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] ${activeTab === tab ? 'bg-[var(--color-surface-hover)] text-[var(--color-text-primary)]' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              <Icon size={16} />
              <span>{label}</span>
            </button>
          ))}
        </div>

        {/* Content area */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {activeTab === 'list' ? (
            <PromptListTab
              prompts={prompts}
              loading={promptsLoading}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onHistory={handleHistory}
            />
          ) : (
            <VersionHistoryTab
              versions={versions}
              loading={versionsLoading}
              onView={handleViewVersion}
              onRollback={handleRollback}
              onBack={handleBackToList}
            />
          )}
        </div>
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
    </div>
  );
}
