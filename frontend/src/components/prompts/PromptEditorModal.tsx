import { useState } from 'react';
import Modal from '../shared/Modal';
import { useTranslation } from 'react-i18next';
import type { PromptItem } from '../../api/client/prompts';

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

function getInitialState(initial: PromptItem | null) {
  if (initial) {
    return {
      name: initial.name,
      description: initial.description || '',
      category: initial.category,
      status: initial.status,
      content: initial.content,
    };
  }
  return { name: '', description: '', category: 'user', status: 'active', content: '' };
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
  const [name, setName] = useState(() => getInitialState(initial).name);
  const [description, setDescription] = useState(() => getInitialState(initial).description);
  const [category, setCategory] = useState(
    () => getInitialState(initial).category,
  );
  const [status, setStatus] = useState(() => getInitialState(initial).status);
  const [content, setContent] = useState(
    () => getInitialState(initial).content,
  );

  const handleSave = () => {
    if (!name.trim()) return;
    onSave({ name: name.trim(), description: description.trim() || undefined, category, content, status });
  };

  return (
    <Modal
      title={
        mode === 'new' ? t('prompts.editor.new') : t('prompts.editor.edit')
      }
      onClose={onClose}
      ariaLabel={
        mode === 'new' ? t('prompts.editor.new') : t('prompts.editor.edit')
      }
      width={520}
      hideHeaderBorder
      bodyClassName="p-6"
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

        {/* Name */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-[var(--color-text-primary)]">
            {t('prompts.editor.name')}
          </label>
          <input
            type="text"
            className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        {/* Description */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-[var(--color-text-primary)]">
            {t('prompts.editor.description')}
          </label>
          <input
            type="text"
            className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        {/* Category + Status row */}
        <div className="flex gap-4">
          <div className="flex flex-col gap-1.5 flex-1">
            <label className="text-sm font-medium text-[var(--color-text-primary)]">
              {t('prompts.editor.category')}
            </label>
            <select
              className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)] cursor-pointer"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="system">system</option>
              <option value="user">user</option>
              <option value="meta">meta</option>
            </select>
          </div>
          <div className="flex flex-col gap-1.5 flex-1">
            <label className="text-sm font-medium text-[var(--color-text-primary)]">
              {t('prompts.editor.status')}
            </label>
            <select
              className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)] cursor-pointer"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="active">active</option>
              <option value="inactive">inactive</option>
            </select>
          </div>
        </div>

        {/* Content */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-[var(--color-text-primary)]">
            {t('prompts.editor.content')}
          </label>
          <textarea
            className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)] resize-y min-h-[180px] font-mono"
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
        </div>

        <p className="text-xs text-[var(--color-text-muted)] m-0">
          {t('prompts.editor.saveHint')}
        </p>
      </div>
    </Modal>
  );
}
