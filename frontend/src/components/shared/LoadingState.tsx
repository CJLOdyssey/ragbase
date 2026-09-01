import { useTranslation } from 'react-i18next';

interface LoadingStateProps {
  message?: string;
  centered?: boolean;
}

export default function LoadingState({ message, centered = false }: LoadingStateProps) {
  const { t } = useTranslation();
  return (
    <div role="status" aria-live="polite" className={`flex items-center justify-center ${centered ? 'h-full' : 'py-12'}`}>
      <p className="text-sm text-[var(--color-text-muted)]">
        {message ?? t('common.loading')}
      </p>
    </div>
  );
}
