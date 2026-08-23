import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle } from 'lucide-react';
import LoadingState from '../shared/LoadingState';

interface Props {
  loading: boolean;
  error: boolean;
  ready: boolean;
  onRetry: () => void;
  children: ReactNode;
}

/** 面板级异步闸门：统一失败重试与加载态，数据就绪后才渲染 children。 */
export default function DataGate({
  loading,
  error,
  ready,
  onRetry,
  children,
}: Props) {
  const { t } = useTranslation();

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 py-10">
        <AlertTriangle
          size={24}
          className="text-[var(--color-warning, #d97706)]"
        />
        <span className="text-sm text-[var(--color-text-secondary)]">
          {t('monitoring.loadFailed')}
        </span>
        <button
          type="button"
          className="px-3 py-1.5 rounded-md text-sm cursor-pointer border-none bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          onClick={onRetry}
          data-testid="monitoring-retry"
        >
          {t('common.retry')}
        </button>
      </div>
    );
  }
  if (loading || !ready) {
    return <LoadingState centered={true} />;
  }
  return <>{children}</>;
}
