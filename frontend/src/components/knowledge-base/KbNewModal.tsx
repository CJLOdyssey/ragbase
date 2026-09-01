import { useEffect, useMemo } from 'react';
import MobileModal from '../shared/MobileModal';
import { Alert, Form, Input, Select } from 'antd';
import { useTranslation } from 'react-i18next';
import type {
  KnowledgeBase,
  ParserConfigForm,
} from '../../api/client/knowledgeBases';
import type { ModelInfo } from '../../api/client/models';
import ChunkingFields from './ChunkingFields';

/** 模型查询状态 — 集中管理加载/错误状态 */
interface ModelsState {
  models: ModelInfo[];
  loading: boolean;
  error: boolean;
}

export interface KbNewModalProps {
  open: boolean;
  mode: 'create' | 'edit';
  /** Edit target; omitted in create mode. */
  kb?: KnowledgeBase | null;
  /** Indexed-asset count — drives the rebuild warning on config change. */
  indexedCount: number;
  modelsState: ModelsState;
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
function EmbedModelFields({ modelsState }: { modelsState: ModelsState }) {
  const { t } = useTranslation();
  const bindable = useMemo(
    () => modelsState.models.filter((m) => m.type === 'embedding'),
    [modelsState.models],
  );
  return (
    <Form.Item
      name="embedModel"
      required
      extra={
        <span className="text-[11px] text-[var(--color-text-muted)]">
          {t('kb.embedModelHint')}
        </span>
      }
      rules={[{ required: true, message: t('kb.embedModelRequired') }]}
      className="!mb-0"
    >
      <Select
        loading={modelsState.loading}
        showSearch={false}
        placeholder={
          modelsState.error
            ? t('kb.embedModelsLoadFailed')
            : bindable.length === 0
              ? t('kb.noEmbedModels')
              : t('kb.embedModelPlaceholder')
        }
        notFoundContent={
          modelsState.error
            ? t('kb.embedModelsLoadFailed')
            : t('kb.noEmbedModels')
        }
        options={bindable.map((m) => ({
          value: m.id,
          label: m.label || m.id,
        }))}
        className="!rounded-lg"
      />
    </Form.Item>
  );
}

export default function KbNewModal({
  open,
  mode,
  kb = null,
  indexedCount,
  modelsState,
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
    () =>
      modelsState.models.filter((m) => m.type === 'embedding').find(Boolean)
        ?.id,
    [modelsState.models],
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
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium cursor-pointer border border-[var(--color-border)] transition-colors duration-150 bg-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
          >
            {t('confirm.cancel')}
          </button>
          <button
            type="button"
            onClick={handleOk}
            disabled={saving}
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium cursor-pointer border-none transition-all duration-150 bg-[var(--color-accent)] text-white hover:brightness-110 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:brightness-100"
          >
            {saving && (
              <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            )}
            {saving ? t('confirm.saving') : t('confirm.confirm')}
          </button>
        </>
      }
    >
      <Form form={form} layout="vertical" requiredMark={false} className="pt-2">
        {/* 基本信息 */}
        <div className="mb-4">
          <h4 className="m-0 mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
            {t('kb.sectionBasic')}
          </h4>
          <div className="flex flex-col gap-1">
            <Form.Item
              name="name"
              label={t('kb.name')}
              rules={[{ required: true, message: t('kb.nameRequired') }]}
              className="!mb-0"
            >
              <Input
                placeholder={t('kb.namePlaceholder')}
                className="!bg-[var(--color-surface)] !border-[var(--color-border)] !rounded-lg"
              />
            </Form.Item>

            <Form.Item
              name="description"
              label={t('kb.description')}
              className="!mb-0"
            >
              <Input.TextArea
                rows={2}
                placeholder={t('kb.descriptionPlaceholder')}
                className="!bg-[var(--color-surface)] !border-[var(--color-border)] !rounded-lg resize-none"
              />
            </Form.Item>
          </div>
        </div>

        {/* 嵌入模型 */}
        <div className="mb-4">
          <h4 className="m-0 mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
            {t('kb.sectionEmbedModel')}
          </h4>
          <EmbedModelFields modelsState={modelsState} />
        </div>

        {/* 分块配置 */}
        <div className="mb-2">
          <h4 className="m-0 mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
            {t('kb.sectionChunking')}
          </h4>
          <ChunkingFields />
        </div>

        {willRebuild && (
          <Alert
            type="warning"
            showIcon
            message={t('kb.changeModelWarning', { count: indexedCount })}
            className="!mt-4 !rounded-lg"
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
