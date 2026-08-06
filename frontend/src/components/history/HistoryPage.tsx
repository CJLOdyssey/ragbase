import EmptyState from '../shared/EmptyState';
import { FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useSessions } from '../../api/hooks';
import { formatDateTime } from '../../utils/formatDateTime';

export default function HistoryPage() {
  const { t } = useTranslation();
  const { data: sessions = [], isLoading } = useSessions();

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
        ) : sessions.length === 0 ? (
          <EmptyState
            icon={<FileText size={24} />}
            description={t('history.empty')}
          />
        ) : (
          <ul className="flex flex-col gap-2" data-testid="history-list">
            {sessions.map((session) => (
              <li
                key={session.id}
                className="flex items-center gap-4 px-4 py-3 rounded-lg bg-[var(--color-surface-raised)]"
                data-testid={`history-item-${session.id}`}
              >
                <span className="flex-1 min-w-0 text-sm text-[var(--color-text-primary)] truncate">
                  {session.title}
                </span>
                <span className="text-xs text-[var(--color-text-muted)] whitespace-nowrap">
                  {session.run_count} runs
                </span>
                <span className="text-xs text-[var(--color-text-muted)] whitespace-nowrap">
                  {formatDateTime(
                    session.updated_at ?? session.created_at ?? '',
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
