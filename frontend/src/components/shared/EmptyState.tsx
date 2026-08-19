import type * as React from 'react';
import { Inbox } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title?: string;
  description?: string;
  action?: React.ReactNode;
  centered?: boolean;
}

export default function EmptyState({
  icon,
  title,
  description,
  action,
  centered = false,
}: EmptyStateProps) {
  const { t } = useTranslation();
  return (
    <div className={`flex flex-col items-center justify-center px-6 text-center ${centered ? 'h-full' : 'py-12'}`}>
      <div className="w-12 h-12 rounded-full bg-[var(--color-surface-hover)] flex items-center justify-center mb-4 text-[var(--color-text-muted)]">
        {icon || <Inbox size={24} />}
      </div>
      <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-1">
        {title || t('common.noData')}
      </h3>
      {description && (
        <p className="text-sm text-[var(--color-text-muted)] max-w-sm mb-4">
          {description}
        </p>
      )}
      {action}
    </div>
  );
}
