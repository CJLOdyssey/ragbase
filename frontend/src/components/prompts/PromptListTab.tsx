import EmptyState from '../shared/EmptyState';
import { FileText, History, Pencil, ShieldAlert, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { PromptItem } from '../../api/client/prompts';

interface Props {
  prompts: PromptItem[];
  loading: boolean;
  onEdit: (row: PromptItem) => void;
  onDelete: (row: PromptItem) => void;
  onHistory: (row: PromptItem) => void;
}

export default function PromptListTab({
  prompts,
  loading,
  onEdit,
  onDelete,
  onHistory,
}: Props) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <p className="text-sm text-[var(--color-text-muted)] p-6">
        {t('history.loading')}
      </p>
    );
  }

  if (prompts.length === 0) {
    return (
      <EmptyState
        icon={<FileText size={24} />}
        title={t('prompts.list.empty')}
      />
    );
  }

  return (
    <div className="p-6">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
            <th className="pb-2 font-medium">{t('prompts.editor.name')}</th>
            <th className="pb-2 font-medium">{t('prompts.editor.category')}</th>
            <th className="pb-2 font-medium">{t('prompts.tab.version')}</th>
            <th className="pb-2 font-medium">{t('prompts.editor.status')}</th>
            <th className="pb-2 font-medium text-right" />
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
              <td className="py-3 pr-4 text-[var(--color-text-secondary)]">
                {row.category}
              </td>
              <td className="py-3 pr-4 text-[var(--color-text-secondary)]">
                {row.version}
              </td>
              <td className="py-3 pr-4">
                <span
                  className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                    row.status === 'active'
                      ? 'bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)] text-[var(--color-accent)]'
                      : 'bg-[var(--color-surface-hover)] text-[var(--color-text-muted)]'
                  }`}
                >
                  {row.status}
                </span>
              </td>
              <td className="py-3">
                <div className="flex items-center justify-end gap-1">
                  <button
                    className="text-xs px-2 py-1 rounded-md cursor-pointer border-none bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
                    onClick={() => onEdit(row)}
                    title={t('prompts.list.edit')}
                  >
                    <Pencil size={13} />
                  </button>
                  <button
                    className="text-xs px-2 py-1 rounded-md cursor-pointer border-none bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
                    onClick={() => onDelete(row)}
                    title={t('prompts.list.delete')}
                  >
                    <Trash2 size={13} />
                  </button>
                  <button
                    className="text-xs px-2 py-1 rounded-md cursor-pointer border-none bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
                    onClick={() => onHistory(row)}
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
  );
}
