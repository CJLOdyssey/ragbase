import { useTranslation } from 'react-i18next';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { STATUS_COLORS, statusColor, withAlpha } from '../shared/statusColors';
import type { QualityAlert } from '../../types/monitoring';
import { formatAlertValue } from './formatters';

/** 告警规则摘要卡：无告警显示绿色就绪态，有告警逐条展示当前值 vs 阈值。 */
export default function AlertsSummaryCard({ alerts }: { alerts: QualityAlert[] }) {
  const { t } = useTranslation();
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-5">
      <h2 className="flex items-center gap-2 m-0 mb-4 text-sm font-medium text-[var(--color-text-primary)]">
        <AlertTriangle
          size={16}
          className="text-[var(--color-warning, #d97706)]"
        />
        {t('monitoring.alertsSectionTitle')}
      </h2>
      {alerts.length === 0 ? (
        <div
          className="flex items-center gap-2 px-3 py-2.5 rounded-lg"
          style={{
            borderColor: withAlpha(STATUS_COLORS.green, 0.18),
            backgroundColor: withAlpha(STATUS_COLORS.green, 0.06),
            borderWidth: 1,
            borderStyle: 'solid',
          }}
        >
          <CheckCircle2
            size={16}
            className="text-[var(--color-accent)]"
          />
          <span className="text-xs text-[var(--color-text-secondary)]">
            {t('monitoring.alerts.none')}
          </span>
        </div>
      ) : (
        <ul
          className="flex flex-col gap-2"
          data-testid="alerts-section"
        >
          {alerts.map((alert) => (
            <li
              key={alert.code}
              className="flex items-center justify-between px-3 py-2 rounded-lg bg-[var(--color-surface-elevated)] border border-[var(--color-border)]"
              data-testid={`alert-${alert.code}`}
            >
              <span className="text-xs text-[var(--color-text-secondary)]">
                {t(`monitoring.alerts.${alert.code}`, {
                  current: formatAlertValue(alert.code, alert.current),
                  threshold: formatAlertValue(alert.code, alert.threshold),
                })}
              </span>
              <span
                className="inline-block w-2 h-2 rounded-full"
                style={{
                  background: statusColor(alert.level),
                  boxShadow: `0 0 5px ${statusColor(alert.level)}80`,
                }}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
