import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Modal as AntdModal } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  listPromptCategories,
  type PromptItem,
} from '../../api/client/prompts';

interface Props {
  mode: 'new' | 'edit';
  initial: PromptItem | null;
  onSave: (payload: {
    name: string;
    description?: string;
    category: string;
    content: string;
    model?: string;
    status?: string;
  }) => void;
  onClose: () => void;
  saving: boolean;
  error: string | null;
}

const STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'draft', label: '草稿' },
  { value: 'published', label: '启用' },
];

/** categories 接口失败时的兜底选项，与后端 /prompts/categories 保持一致。 */
const FALLBACK_CATEGORIES = [
  { value: 'system', label: '系统提示词' },
  { value: 'user', label: '用户提示词' },
  { value: 'meta', label: '元提示词' },
];

function statusToUi(status: string): string {
  if (status === 'published' || status === 'active') return 'published';
  if (status === 'draft' || status === 'inactive') return 'draft';
  return 'draft';
}

function uiToStatus(ui: string): string {
  return ui === 'published' ? 'published' : 'draft';
}

function getInitialState(initial: PromptItem | null) {
  if (initial) {
    return {
      name: initial.name,
      description: initial.description || '',
      category: initial.category || 'user',
      status: statusToUi(initial.status),
      content: initial.content,
      version: initial.version || 'v1.0.0',
    };
  }
  return {
    name: '',
    description: '',
    category: 'user',
    status: 'draft',
    content: '',
    version: 'v1.0.0',
  };
}

export default function PromptEditorModal({
  mode,
  initial,
  onSave,
  onClose,
  saving,
  error,
}: Props) {
  const { t } = useTranslation();
  const init = getInitialState(initial);
  const [name, setName] = useState(init.name);
  const [description, setDescription] = useState(init.description);
  const [category, setCategory] = useState(init.category);
  const [statusUi, setStatusUi] = useState(init.status);
  const [content, setContent] = useState(init.content);

  // 分类选项来自后端单一事实源；失败时回退到与后端一致的本地兜底
  const { data: categories } = useQuery({
    queryKey: ['prompt-categories'],
    queryFn: listPromptCategories,
    staleTime: 5 * 60 * 1000,
  });
  const categoryOptions = categories ?? FALLBACK_CATEGORIES;

  // 版本由后端保存时递增，前端只读展示、不参与提交
  const version = init.version;

  const handleSave = () => {
    if (!name.trim()) return;
    onSave({
      name: name.trim(),
      description: description.trim() || undefined,
      category,
      content,
      status: uiToStatus(statusUi),
    });
  };

  return (
    <AntdModal
      title={
        <span className="flex items-center gap-2.5 min-w-0 pr-4">
          <span className="truncate">
            {mode === 'new'
              ? t('prompts.editor.new')
              : t('prompts.editor.edit')}
          </span>
          {mode === 'edit' && (
            <span className="shrink-0 text-xs font-mono text-[var(--color-text-tertiary)]">
              {version}
            </span>
          )}
        </span>
      }
      open={true}
      onCancel={onClose}
      centered
      width={520}
      footer={
        <>
          <button
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
            onClick={onClose}
            disabled={saving}
          >
            {t('confirm.cancel')}
          </button>
          <button
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-accent)] text-white hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
            onClick={handleSave}
            disabled={saving || !name.trim()}
          >
            {saving ? t('prompts.editor.saving') : t('prompts.editor.save')}
          </button>
        </>
      }
    >
      <div className="flex flex-col gap-4 p-6">
        {error && (
          <div className="bg-[color-mix(in_srgb,var(--color-danger)_10%,transparent)] border border-[color-mix(in_srgb,var(--color-danger)_25%,transparent)] rounded-lg py-2.5 px-3.5 text-[var(--color-danger)] text-sm">
            {error}
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-[var(--color-text-primary)]">
            名称
          </label>
          <input
            type="text"
            placeholder="如：产品问答助手"
            className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-[var(--color-text-primary)]">
            描述
          </label>
          <input
            type="text"
            placeholder="简短描述此提示词的用途"
            className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-[var(--color-text-primary)]">
            提示词模板
          </label>
          <textarea
            placeholder="你是一位…{{context}}…{{question}}"
            rows={6}
            className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)] resize-y min-h-[140px] font-mono leading-[1.6]"
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--color-text-primary)]">
              {t('prompts.editor.category')}
            </label>
            <select
              className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)] cursor-pointer"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {categoryOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--color-text-primary)]">
              {t('prompts.editor.status')}
            </label>
            <select
              className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)] cursor-pointer"
              value={statusUi}
              onChange={(e) => setStatusUi(e.target.value)}
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <p className="text-xs text-[var(--color-text-muted)] m-0">
          {t('prompts.editor.saveHint')}
        </p>
      </div>
    </AntdModal>
  );
}
