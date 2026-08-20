import { useTranslation } from 'react-i18next';
import Sparkline from './Sparkline';

export interface KpiCardProps {
  label: string;
  value: string;
  color: string;
  spark: number[];
  hasData: boolean;
  sparkId: string;
}

export default function KpiCard({
  label,
  value,
  color,
  spark,
  hasData,
  sparkId,
}: KpiCardProps) {
  const { t } = useTranslation();
  return (
    <div className="relative overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-4">
      <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
        {label}
      </div>
      <div
        className="mb-1.5 text-2xl font-bold tracking-[-0.04em]"
        style={{ color: hasData ? color : 'var(--color-text-muted)' }}
      >
        {value}
      </div>
      <Sparkline
        values={spark}
        color={color}
        fillId={sparkId}
        width={120}
        height={28}
        strokeWidth={1.5}
      />
      <div className="mt-1 font-mono text-[11px] text-[var(--color-text-muted)]">
        {hasData ? '' : t('monitoring.noData')}
      </div>
    </div>
  );
}
