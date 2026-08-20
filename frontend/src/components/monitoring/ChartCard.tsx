import Sparkline from './Sparkline';

export interface ChartCardProps {
  title: string;
  label: string;
  color: string;
  values: number[];
  chartId: string;
  invert?: boolean;
}

export default function ChartCard({
  title,
  label,
  color,
  values,
  chartId,
  invert = false,
}: ChartCardProps) {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="m-0 text-sm font-medium text-[var(--color-text-primary)]">
          {title}
        </h3>
        <span className="font-mono text-[11px] text-[var(--color-text-muted)]">
          {label}
        </span>
      </div>
      <Sparkline
        values={values}
        color={color}
        fillId={chartId}
        width={320}
        height={120}
        strokeWidth={2}
        invert={invert}
      />
    </div>
  );
}
