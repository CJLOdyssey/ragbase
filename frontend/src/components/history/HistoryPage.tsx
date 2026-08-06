import EmptyState from '../shared/EmptyState';
import { useQuery } from '@tanstack/react-query';
import { FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { listGenerations } from '../../api/client/generations';
import { formatDateTime } from '../../utils/formatDateTime';

export default function HistoryPage() {
  const { t } = useTranslation();
  const { data: items = [], isLoading } = useQuery({
    queryKey: ['generations'],
    queryFn: () => listGenerations(),
  });

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-[var(--color-border)]">
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)] m-0">
          {t('history.title')}
        </h1>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 p-6">
        {isLoading ? (
          <p className="text-sm text-[var(--color-text-muted)]">
            {t('history.loading')}
          </p>
        ) : items.length === 0 ? (
          <EmptyState
            icon={<FileText size={24} />}
            description={t('history.empty')}
          />
        ) : (
          <ul className="flex flex-col gap-2">
            {items.map((item) => (
              <li
                key={item.run_id}
                className="flex items-center gap-4 px-4 py-3 rounded-lg bg-[var(--color-surface-raised)]"
              >
                <span className="flex-1 min-w-0 text-sm text-[var(--color-text-primary)] truncate">
                  {item.topic}
                </span>
                <span className="text-xs text-[var(--color-text-muted)] whitespace-nowrap">
                  {t(`history.type_${item.content_type}`, {
                    defaultValue: t('history.type_generic'),
                  })}
                </span>
                <span className="text-xs text-[var(--color-text-muted)] whitespace-nowrap">
                  {formatDateTime(item.created_at ?? '')}
                </span>
                {/* TODO: enable when a run detail page exists (backend has none yet) */}
                <button
                  type="button"
                  disabled
                  className="text-xs px-2 py-1 rounded text-[var(--color-text-muted)] cursor-not-allowed"
                >
                  {t('history.actions.view')}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
