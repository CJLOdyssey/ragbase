import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  createPrompt,
  deletePrompt,
  listPrompts,
  updatePrompt,
  type PromptItem,
} from '../../api/client/prompts';
import { listVersions, type VersionItem } from '../../api/client/versions';
import { useToast } from '../../utils/useToast';

export type PromptTab = 'all' | 'published' | 'draft';

export interface DialogState {
  type: 'new' | 'edit' | 'delete' | 'version-view';
  row?: PromptItem;
  version?: VersionItem;
}

const FILTER_STRATEGY: Record<PromptTab, (p: PromptItem) => boolean> = {
  all: () => true,
  published: (p) => p.status === 'published' || p.status === 'active',
  draft: (p) => p.status !== 'published' && p.status !== 'active',
};

export type PromptView = 'table' | 'grid';

export function usePromptLibrary() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [historyPrompt, setHistoryPrompt] = useState<PromptItem | null>(null);
  const [detailPrompt, setDetailPrompt] = useState<PromptItem | null>(null);
  const [dialog, setDialog] = useState<DialogState | null>(null);
  const [tab, setTab] = useState<PromptTab>('all');
  const [search, setSearch] = useState('');
  const [view, setView] = useState<PromptView>('table');

  const promptsQuery = useQuery({
    queryKey: ['prompts'],
    queryFn: listPrompts,
  });

  const versionsQuery = useQuery({
    queryKey: ['versions', historyPrompt?.id],
    queryFn: () => listVersions('prompt', historyPrompt!.id),
    enabled: !!historyPrompt,
  });

  const rawPrompts = promptsQuery.data;
  const rawVersions = versionsQuery.data;
  const prompts = useMemo(() => rawPrompts ?? [], [rawPrompts]);
  const versions = useMemo(() => rawVersions ?? [], [rawVersions]);

  const counts = useMemo(() => {
    const all = prompts.length;
    const published = prompts.filter(FILTER_STRATEGY.published).length;
    return { all, published, draft: all - published };
  }, [prompts]);

  const filtered = useMemo(() => {
    const byTab = prompts.filter(FILTER_STRATEGY[tab]);
    if (!search.trim()) return byTab;
    const q = search.trim().toLowerCase();
    return byTab.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        (p.description ?? '').toLowerCase().includes(q) ||
        p.content.toLowerCase().includes(q),
    );
  }, [prompts, tab, search]);

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
      toast(t('toast.deleteSuccess'), 'success');
    },
    onError: () => toast(t('toast.deleteFailed'), 'error'),
  });

  const handleSave = (payload: Parameters<typeof createPrompt>[0]) => {
    if (dialog?.type === 'new') createMutation.mutate(payload);
    else if (dialog?.type === 'edit' && dialog.row)
      updateMutation.mutate({ id: dialog.row.id, payload });
  };

  const handleRollback = (v: VersionItem) => {
    const targetId = historyPrompt?.id;
    if (!targetId) return;
    const snap = v.snapshot as Record<string, string>;
    updateMutation.mutate({
      id: targetId,
      payload: {
        name: snap.name ?? '',
        category: snap.category ?? 'user',
        content: snap.content ?? '',
      },
    });
  };

  return {
    prompts,
    filtered,
    counts,
    tab,
    setTab,
    search,
    setSearch,
    view,
    setView,
    isLoading: promptsQuery.isLoading,
    historyPrompt,
    setHistoryPrompt,
    detailPrompt,
    setDetailPrompt,
    versions,
    dialog,
    setDialog,
    handleSave,
    handleRollback,
    createMutation,
    updateMutation,
    deleteMutation,
    isSaving: createMutation.isPending || updateMutation.isPending,
    saveError:
      createMutation.isError || updateMutation.isError
        ? t('prompts.editor.saveFailed')
        : null,
  };
}
