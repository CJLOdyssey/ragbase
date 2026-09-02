import { useTranslation } from 'react-i18next';
import {
  MONITORING_TABS,
  type MonitoringTabKey,
} from './useMonitoringTab';

interface Props {
  tab: MonitoringTabKey;
  onChange: (next: MonitoringTabKey) => void;
}

export default function MonitoringTabs({ tab, onChange }: Props) {
  const { t } = useTranslation();
  return (
    <div
      role="tablist"
      className="flex flex-wrap items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-1"
      data-testid="monitoring-tabs"
    >
      {MONITORING_TABS.map(({ key, labelKey }) => {
        const active = tab === key;
        return (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={active}
            className={`px-3 py-1.5 rounded-md text-sm cursor-pointer border-none transition-colors duration-150 ${
              active
                ? 'bg-[var(--color-accent)] text-[var(--color-text-on-accent)]'
                : 'bg-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
            }`}
            onClick={() => onChange(key)}
            data-testid={`monitoring-tab-${key}`}
          >
            {t(labelKey)}
          </button>
        );
      })}
    </div>
  );
}
