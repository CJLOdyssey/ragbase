import { useEffect, useMemo } from 'react';
import { Alert, Form, Input, Select } from 'antd';
import { useTranslation } from 'react-i18next';
import MobileModal from '../shared/MobileModal';
import type {
  KnowledgeBase,
  ParserConfigForm,
} from '../../api/client/knowledgeBases';
import type { ModelInfo } from '../../api/client/models';
import ChunkingFields from './ChunkingFields';

export interface KbNewModalProps {
  open: boolean;
  mode: 'create' | 'edit';
  /** Edit target; omitted in create mode. */
  kb?: KnowledgeBase | null;
  /** Indexed-asset count — drives the rebuild warning on config change. */
  indexedCount: number;
  models: ModelInfo[];
  modelsLoading?: boolean;
  /** 嵌入模型查询失败：Select 显示错误占位而非误导性「无可用模型」 */
  modelsError?: boolean;
  saving: boolean;
  onClose: () => void;
  onSave: (
    name: string,
    description: string,
    embedModel: string,
    parserConfig: ParserConfigForm,
  ) => void;
}

const DEFAULT_CHUNK_SIZE = 512;
const DEFAULT_OVERLAP = 64;

function getInitialFields(kb: KnowledgeBase | null): {
  name: string;
  description: string;
  embedModel: string;
  config: ParserConfigForm;
} {
  return {
    name: kb?.name ?? '',
    description: kb?.description ?? '',
    embedModel: kb?.embedModel ?? '',
    config: {
      chunkSize: kb?.parserConfig?.chunk_size ?? DEFAULT_CHUNK_SIZE,
      overlap: kb?.parserConfig?.overlap ?? DEFAULT_OVERLAP,
    },
  };
}

interface FormValues {
  name?: string;
  description?: string;
  embedModel?: string;
  chunkSize?: number;
  overlap?: number;
}

/** Rebuild is needed when a bound KB's model or chunking params change. */
function computeWillRebuild(
  mode: KbNewModalProps['mode'],
  indexedCount: number,
  values: FormValues | null,
  initialEmbedModel: string,
  initialConfig: ParserConfigForm,
): boolean {
  const v = values ?? {};
  if (mode !== 'edit' || indexedCount === 0) return false;
  const modelChanged =
    Boolean(v.embedModel) && v.embedModel !== initialEmbedModel;
  const configChanged =
    (v.chunkSize ?? initialConfig.chunkSize) !== initialConfig.chunkSize ||
    (v.overlap ?? initialConfig.overlap) !== initialConfig.overlap;
  return modelChanged || configChanged;
}

function submitValues(
  values: FormValues,
  onSave: KbNewModalProps['onSave'],
): void {
  const name = values.name?.trim();
  if (!name || !values.embedModel) return;
  onSave(
    name,
    values.description?.trim() ?? '',
    values.embedModel,
    buildParserConfig(values),
  );
}

/** Embedding-model picker — only type==='embedding' models are bindable. */
function EmbedModelFields({
  models,
  modelsLoading,
  modelsError = false,
}: {
  models: ModelInfo[];
  modelsLoading: boolean;
  modelsError?: boolean;
}) {
  const { t } = useTranslation();
  const bindable = useMemo(
    () => models.filter((m) => m.type === 'embedding'),
    [models],
  );
  return (
    <Form.Item
      name="embedModel"
      label={t('kb.embedModel')}
      required
      extra={t('kb.embedModelHint')}
      rules={[{ required: true, message: t('kb.embedModelRequired') }]}
    >
      <Select
        loading={modelsLoading}
        showSearch={false}
        placeholder={
          modelsError
            ? t('kb.embedModelsLoadFailed')
            : bindable.length === 0
              ? t('kb.noEmbedModels')
              : t('kb.embedModelPlaceholder')
        }
        notFoundContent={
          modelsError ? t('kb.embedModelsLoadFailed') : t('kb.noEmbedModels')
        }
        options={bindable.map((m) => ({
          value: m.id,
          label: m.label || m.id,
        }))}
      />
    </Form.Item>
  );
}

export default function KbNewModal({
  open,
  mode,
  kb = null,
  indexedCount,
  models,
  modelsLoading = false,
  modelsError = false,
  saving,
  onClose,
  onSave,
}: KbNewModalProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const initial = getInitialFields(kb);

  // Fill only EMPTY fields on open — idempotent across re-renders and
  // never clobbers user input; embedModel falls back to the first key model.
  const firstEmbeddingId = useMemo(
    () => models.filter((m) => m.type === 'embedding').find(Boolean)?.id,
    [models],
  );

  useEffect(() => {
    if (!open) return;
    const cur = form.getFieldsValue([
      'name',
      'description',
      'embedModel',
      'chunkSize',
      'overlap',
    ]) as FormValues;
    const patch: Partial<FormValues> = {};
    if (cur.chunkSize == null) patch.chunkSize = initial.config.chunkSize;
    if (cur.overlap == null) patch.overlap = initial.config.overlap;
    if (mode === 'edit') {
      if (cur.name == null) patch.name = initial.name;
      if (cur.description == null) patch.description = initial.description;
    }
    const modelFallback =
      mode === 'edit'
        ? initial.embedModel
        : initial.embedModel || firstEmbeddingId;
    if (modelFallback && !cur.embedModel) patch.embedModel = modelFallback;
    if (Object.keys(patch).length > 0) form.setFieldsValue(patch);
  }, [open, mode, form, initial, firstEmbeddingId]);

  const watched = Form.useWatch((values: FormValues) => values, form);

  function handleOk() {
    void form
      .validateFields()
      .then((values) => submitValues(values as FormValues, onSave));
  }

  const willRebuild = computeWillRebuild(
    mode,
    indexedCount,
    watched,
    initial.embedModel,
    initial.config,
  );

  return (
    <MobileModal
      open={open}
      onClose={onClose}
      mode="sheet"
      title={mode === 'create' ? t('kb.createTitle') : t('kb.editTitle')}
      width={480}
      footer={
        <>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
          >
            {t('confirm.cancel')}
          </button>
          <button
            type="button"
            onClick={handleOk}
            disabled={saving}
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-accent)] text-white hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {saving ? '...' : t('confirm.confirm')}
          </button>
        </>
      }
    >
      <Form form={form} layout="vertical" requiredMark={false} className="pt-2">
        <Form.Item
          name="name"
          label={t('kb.name')}
          rules={[{ required: true, message: t('kb.nameRequired') }]}
        >
          <Input
            placeholder={t('kb.namePlaceholder')}
            className="!bg-[var(--color-surface)] !border-[var(--color-border)] !text-[var(--color-text-primary)]"
          />
        </Form.Item>

        <Form.Item name="description" label={t('kb.description')}>
          <Input.TextArea
            rows={3}
            placeholder={t('kb.descriptionPlaceholder')}
            className="!bg-[var(--color-surface)] !border-[var(--color-border)] !text-[var(--color-text-primary)] resize-none"
          />
        </Form.Item>

        <EmbedModelFields
          models={models}
          modelsLoading={modelsLoading}
          modelsError={modelsError}
        />

        <ChunkingFields />

        {willRebuild && (
          <Alert
            type="warning"
            showIcon
            message={t('kb.changeModelWarning', { count: indexedCount })}
            className="!mb-2"
          />
        )}
      </Form>
    </MobileModal>
  );
}

function buildParserConfig(v: FormValues): ParserConfigForm {
  return {
    chunkSize: v.chunkSize ?? DEFAULT_CHUNK_SIZE,
    overlap: v.overlap ?? DEFAULT_OVERLAP,
  };
}
