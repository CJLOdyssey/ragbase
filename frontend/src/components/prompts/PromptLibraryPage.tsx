import { useState } from 'react';
import ConfirmDialog from '../shared/ConfirmDialog';
import EmptyState from '../shared/EmptyState';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText, History, Pencil, ShieldAlert, Trash2 } from 'lucide-react';
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
import VersionViewModal from './VersionViewModal';
import { useToast } from '../../utils/useToast';

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

  const [selectedPromptId, setSelectedPromptId] = useState<string | null>(null);
  const [dialog, setDialog] = useState<DialogState | null>(null);

  const { data: prompts = [], isLoading } = useQuery({
    queryKey: ['prompts'],
    queryFn: listPrompts,
  });

  const { data: versions = [] } = useQuery({
    queryKey: ['versions', selectedPromptId],
    queryFn: () => listVersions('prompt', selectedPromptId!),
    enabled: selectedPromptId !== null,
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
        <button
          className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-accent)] text-white hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
          onClick={handleNew}
        >
          {t('prompts.editor.new')}
        </button>
      </div>

      {/* Content area */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {isLoading ? (
          <LoadingState centered={true} />
        ) : prompts.length === 0 ? (
          <EmptyState
            icon={<FileText size={24} />}
            title={t('prompts.list.empty')}
            description={t('prompts.list.emptyDesc')}
            centered={true}
          />
        ) : (
          <div className="p-6">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
                  <th className="pb-2 font-medium">{t('prompts.editor.name')}</th>
                  <th className="pb-2 font-medium">{t('prompts.editor.description')}</th>
                  <th className="pb-2 font-medium">{t('prompts.tab.version')}</th>
                  <th className="pb-2 font-medium">{t('prompts.editor.updatedAt')}</th>
                  <th className="pb-2 font-medium text-right">{t('prompts.editor.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {prompts.map((row) => (
                  <tr
                    key={row.id}
                    className="border-b border-[var(--color-border)] hover:bg-[var(--color-surface-hover)] transition-colors"
                  >
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <span className="text-[var(--color-text-primary)] font-medium truncate max-w-[220px]">
                          {row.name}
                        </span>
                        {row.category === 'system' && (
                          <ShieldAlert
                            size={14}
                            className="text-[var(--color-text-muted)] shrink-0"
                            aria-label={t('prompts.list.secureNote')}
                          />
                        )}
                      </div>
                    </td>
                    <td className="py-3 pr-4 text-[var(--color-text-secondary)] max-w-[280px] truncate">
                      {row.description || '—'}
                    </td>
                    <td className="py-3 pr-4 text-[var(--color-text-secondary)]">
                      {row.version}
                    </td>
                    <td className="py-3 pr-4 text-[var(--color-text-muted)]">
                      {new Date(row.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          className="text-xs px-2 py-1 rounded-md cursor-pointer border-none bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
                          onClick={() => handleEdit(row)}
                          title={t('prompts.list.edit')}
                        >
                          <Pencil size={13} />
                        </button>
                        <button
                          className="text-xs px-2 py-1 rounded-md cursor-pointer border-none bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
                          onClick={() => handleDelete(row)}
                          title={t('prompts.list.delete')}
                        >
                          <Trash2 size={13} />
                        </button>
                        <button
                          className="text-xs px-2 py-1 rounded-md cursor-pointer border-none bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
                          onClick={() => handleHistory(row)}
                          title={t('prompts.list.history')}
                        >
                          <History size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
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
