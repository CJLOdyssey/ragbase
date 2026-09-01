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
  failed?: number;
  pending?: number;
  totalBytes: number;
  filteredCount?: number;
}

function TotalCard({
  total,
  totalBytes,
}: {
  total: number;
  totalBytes: number;
}) {
  const { t } = useTranslation();
  return (
    <div className="rounded-[12px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-4 py-3.5">
      <div className="text-[10.5px] font-mono font-semibold tracking-[0.07em] uppercase text-[var(--color-text-tertiary)] mb-2">
        {t('assets.stat.total')}
      </div>
      <div className="flex items-baseline gap-1.5">
        <span
          className="text-[24px] font-bold leading-none tracking-[-0.04em]"
          style={{ color: 'var(--color-text-primary)' }}
        >
          {String(total)}
        </span>
        <span className="text-[12px] text-[var(--color-text-secondary)]">
          {t('assets.stat.unit')}
        </span>
      </div>
      <div className="text-[11px] font-mono text-[var(--color-text-tertiary)] mt-1.5">
        {formatBytes(totalBytes)}
      </div>
    </div>
  );
}

export default function AssetsStats({
  total,
  indexed,
  processing,
  failed = 0,
  pending,
  totalBytes,
  filteredCount,
}: AssetsStatsProps) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <TotalCard total={total} totalBytes={totalBytes} />
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
          label={t('assets.status.failed')}
          value={String(failed)}
          unit={t('assets.stat.unit')}
          color={STATUS_COLORS.red}
        />
      </div>
      {typeof filteredCount === 'number' && filteredCount !== total && (
        <div className="text-[11px] font-mono text-[var(--color-text-tertiary)]">
          {t('assets.filterCount', { filteredCount, total })}
        </div>
      )}
      {typeof pending === 'number' && pending > 0 && (
        <div className="text-[11px] text-[var(--color-text-tertiary)] hidden">
          {pending}
        </div>
      )}
    </div>
  );
}
