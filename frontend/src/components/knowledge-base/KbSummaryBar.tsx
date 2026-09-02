import { STATUS_COLORS } from '../shared/statusColors';
import { useTranslation } from 'react-i18next';

export interface KbSummaryBarProps {
  totalKbs: number;
  totalAssets: number;
  indexedRate: number;
}

const ACCENTS = [
  'var(--color-accent)',
  STATUS_COLORS.green,
  STATUS_COLORS.blue,
];

export default function KbSummaryBar({
  totalKbs,
  totalAssets,
  indexedRate,
}: KbSummaryBarProps) {
  const { t } = useTranslation();
  const items = [
    { label: t('kb.summaryTotal'), value: totalKbs, accent: ACCENTS[0] },
    { label: t('kb.summaryAssets'), value: totalAssets, accent: ACCENTS[1] },
    {
      label: t('kb.summaryIndexedRate'),
      value: `${indexedRate}%`,
      accent: ACCENTS[2],
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {items.map((item) => (
        <div
          key={item.label}
          className="flex items-center gap-3.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-4"
        >
          <span
            className="text-[26px] font-bold leading-none tracking-tight"
            style={{ color: item.accent }}
          >
            {item.value}
          </span>
          <span className="text-xs text-[var(--color-text-secondary)]">
            {item.label}
          </span>
        </div>
      ))}
    </div>
  );
}
