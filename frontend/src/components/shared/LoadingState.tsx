import { useTranslation } from 'react-i18next';

interface LoadingStateProps {
  message?: string;
}

export default function LoadingState({ message }: LoadingStateProps) {
  const { t } = useTranslation();
  return (
    <div className="flex items-center justify-center py-12">
      <p className="text-sm text-[var(--color-text-muted)]">
        {message || t('common.loading')}
      </p>
    </div>
  );
}
