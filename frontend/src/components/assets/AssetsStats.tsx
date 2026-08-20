import { STATUS_COLORS } from '../shared/statusColors';
import { useTranslation } from 'react-i18next';
import { formatBytes } from './assetUtils';

interface StatCardProps {
  label: string;
  value: string;
  unit: string;
  color: string;
}

function StatCard({ label, value, unit, color }: StatCardProps) {
  return (
    <div className="rounded-[12px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-4 py-3.5">
      <div className="text-[10.5px] font-mono font-semibold tracking-[0.07em] uppercase text-[var(--color-text-tertiary)] mb-2">
        {label}
      </div>
      <div className="flex items-baseline gap-1.5">
        <span
          className="text-[24px] font-bold leading-none tracking-[-0.04em]"
          style={{ color }}
        >
          {value}
        </span>
        <span className="text-[12px] text-[var(--color-text-secondary)]">
          {unit}
        </span>
      </div>
    </div>
  );
}

interface AssetsStatsProps {
  total: number;
  indexed: number;
  processing: number;
  totalBytes: number;
}

export default function AssetsStats({
  total,
  indexed,
  processing,
  totalBytes,
}: AssetsStatsProps) {
  const { t } = useTranslation();
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <StatCard
        label={t('assets.stat.total')}
        value={String(total)}
        unit={t('assets.stat.unit')}
        color="var(--color-accent)"
      />
      <StatCard
        label={t('assets.stat.indexed')}
        value={String(indexed)}
        unit={t('assets.stat.unit')}
        color={STATUS_COLORS.green}
      />
      <StatCard
        label={t('assets.stat.processing')}
        value={String(processing)}
        unit={t('assets.stat.unit')}
        color={STATUS_COLORS.amber}
      />
      <StatCard
        label={t('assets.stat.totalSize')}
        value={formatBytes(totalBytes)}
        unit=""
        color={STATUS_COLORS.blue}
      />
    </div>
  );
}
