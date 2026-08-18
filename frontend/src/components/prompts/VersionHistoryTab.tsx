import EmptyState from '../shared/EmptyState';
import { ArrowLeft, Eye, RotateCcw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { VersionItem } from '../../api/client/versions';

interface Props {
  versions: VersionItem[];
  loading: boolean;
  onView: (v: VersionItem) => void;
  onRollback: (v: VersionItem) => void;
  onBack: () => void;
}

export default function VersionHistoryTab({
  versions,
  loading,
  onView,
  onRollback,
  onBack,
}: Props) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col h-full p-6">
      {/* Back button */}
      <button
        className="inline-flex items-center gap-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] bg-transparent border-none cursor-pointer mb-4 self-start transition-colors"
        onClick={onBack}
      >
        <ArrowLeft size={14} />
        {t('prompts.version.backToList')}
      </button>

      {loading ? (
        <p className="text-sm text-[var(--color-text-muted)]">
          {t('history.loading')}
        </p>
      ) : versions.length === 0 ? (
        <EmptyState
          title={t('prompts.version.title')}
          description={t('prompts.list.empty')}
        />
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
              <th className="pb-2 font-medium">{t('prompts.tab.version')}</th>
              <th className="pb-2 font-medium">created_at</th>
              <th className="pb-2 font-medium">created_by</th>
              <th className="pb-2 font-medium text-right" />
            </tr>
          </thead>
          <tbody>
            {versions.map((v) => (
              <tr
                key={v.id}
                className="border-b border-[var(--color-border)] hover:bg-[var(--color-surface-hover)] transition-colors"
              >
                <td className="py-3 pr-4 text-[var(--color-text-primary)] font-medium">
                  v{v.version_num}
                </td>
                <td className="py-3 pr-4 text-[var(--color-text-secondary)]">
                  {v.created_at ? new Date(v.created_at).toLocaleString() : '—'}
                </td>
                <td className="py-3 pr-4 text-[var(--color-text-secondary)]">
                  {v.created_by ?? '—'}
                </td>
                <td className="py-3">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      className="text-xs px-2 py-1 rounded-md cursor-pointer border-none bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
                      onClick={() => onView(v)}
                      title={t('prompts.version.view')}
                    >
                      <Eye size={13} />
                    </button>
                    <button
                      className="text-xs px-2 py-1 rounded-md cursor-pointer border-none bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
                      onClick={() => onRollback(v)}
                      title={t('prompts.version.rollback')}
                    >
                      <RotateCcw size={13} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
