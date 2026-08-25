import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  updateKnowledgeBase,
  type ParserConfigForm,
} from '../../api/client/knowledgeBases';
import { useToast } from '../../utils/useToast';

interface Handlers {
  closeForm: () => void;
  closeDelete: () => void;
}

/** KB page mutations — CRUD + asset assignment, with cache invalidation. */
export function useKbMutations({ closeForm, closeDelete }: Handlers) {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: ({
      name,
      description,
      embedModel,
      parserConfig,
    }: {
      name: string;
      description: string;
      embedModel: string;
      parserConfig: ParserConfigForm;
    }) => createKnowledgeBase(name, description, embedModel, parserConfig),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      closeForm();
      toast(t('toast.saveSuccess'), 'success');
    },
    onError: () => toast(t('toast.error'), 'error'),
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      name,
      description,
      embedModel,
      parserConfig,
    }: {
      id: string;
      name: string;
      description: string;
      embedModel?: string | null;
      parserConfig?: ParserConfigForm;
    }) => updateKnowledgeBase(id, name, description, embedModel, parserConfig),
    onSuccess: () => {
      // Model rebind resets assets' indexed flag server-side — refresh both.
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      closeForm();
      toast(t('toast.saveSuccess'), 'success');
    },
    onError: () => toast(t('toast.error'), 'error'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteKnowledgeBase(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      closeDelete();
      toast(t('toast.deleteSuccess'), 'success');
    },
    onError: () => toast(t('toast.deleteFailed'), 'error'),
  });

  // 素材归属动作（assign）归素材页管辖 — KB 页只读呈现统计结果
  return { createMutation, updateMutation, deleteMutation };
}
