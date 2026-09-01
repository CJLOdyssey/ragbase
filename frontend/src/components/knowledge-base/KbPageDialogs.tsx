import ConfirmDialog from '../shared/ConfirmDialog';
import { useTranslation } from 'react-i18next';
import type {
  KnowledgeBase,
  ParserConfigForm,
} from '../../api/client/knowledgeBases';
import type { ModelInfo } from '../../api/client/models';
import KbNewModal from './KbNewModal';
import KbRecallModal from './KbRecallModal';

export interface KbFormState {
  mode: 'create' | 'edit';
  kb?: KnowledgeBase;
}

/** 模型查询状态 — 集中管理加载/错误状态 */
interface ModelsState {
  models: ModelInfo[];
  loading: boolean;
  error: boolean;
}

interface KbPageDialogsProps {
  form: KbFormState | null;
  deleteTarget: KnowledgeBase | null;
  testTarget: KnowledgeBase | null;
  perKb: Map<string, { indexedCount: number }>;
  modelsState: ModelsState;
  saving: boolean;
  onCloseForm: () => void;
  onSave: (
    name: string,
    description: string,
    embedModel: string,
    parserConfig: ParserConfigForm,
  ) => void;
  onDeleteCancel: () => void;
  onDeleteConfirm: () => void;
  onTestClose: () => void;
}

/** 知识库页弹窗编排层 — 对齐 prompts 页 DialogLayer 模式。 */
export default function KbPageDialogs({
  form,
  deleteTarget,
  testTarget,
  perKb,
  modelsState,
  saving,
  onCloseForm,
  onSave,
  onDeleteCancel,
  onDeleteConfirm,
  onTestClose,
}: KbPageDialogsProps) {
  const { t } = useTranslation();
  return (
    <>
      {form && (
        <KbNewModal
          open={true}
          mode={form.mode}
          kb={form.kb ?? null}
          indexedCount={
            form.kb ? (perKb.get(form.kb.id)?.indexedCount ?? 0) : 0
          }
          modelsState={modelsState}
          saving={saving}
          onClose={onCloseForm}
          onSave={onSave}
        />
      )}

      {deleteTarget && (
        <ConfirmDialog
          title={t('confirm.delete')}
          message={t('kb.deleteConfirm')}
          danger
          onConfirm={onDeleteConfirm}
          onCancel={onDeleteCancel}
        />
      )}

      {testTarget && (
        <KbRecallModal
          open={true}
          knowledgeBaseId={testTarget.id}
          knowledgeBaseName={testTarget.name}
          indexedCount={perKb.get(testTarget.id)?.indexedCount ?? 0}
          onClose={onTestClose}
        />
      )}
    </>
  );
}
