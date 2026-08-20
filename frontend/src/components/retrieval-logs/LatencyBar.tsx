import { useTranslation } from 'react-i18next';
import type { RetrievalLogItem } from '../../api/client/retrievalLogs';
import { latencyColor, percentile } from './latency';

interface LatencyBarProps {
  items: RetrievalLogItem[];
}

export default function LatencyBar({ items }: LatencyBarProps) {
  const { t } = useTranslation();
  const latencies = items.map((i) => i.latency_ms);
  const p50 = percentile(latencies, 0.5);
  const p90 = percentile(latencies, 0.9);
  const max = latencies.length ? Math.max(...latencies) : 0;

  const barW = 28;
  const gap = 8;
  const height = 40;
  const width = Math.max(
    1,
    latencies.length * barW + (latencies.length - 1) * gap,
  );
  const maxRef = Math.max(max, 1);

  const stats = [
    { label: 'P50', value: `${p50}ms`, color: latencyColor(p50) },
    { label: 'P90', value: `${p90}ms`, color: latencyColor(p90) },
    { label: 'Max', value: `${max}ms`, color: latencyColor(max) },
  ];

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[13px] font-medium text-[var(--color-text-primary)]">
          {t('retrievalLogs.latencyTrend')}
        </span>
        <div className="flex gap-5">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <div
                className="text-[13px] font-bold font-mono"
                style={{ color: s.color }}
              >
                {s.value}
              </div>
              <div className="text-[10px] text-[var(--color-text-muted)] tracking-wide">
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </div>
      {latencies.length === 0 ? (
        <div className="text-xs text-[var(--color-text-muted)] py-2">
          {t('retrievalLogs.latencyNoData')}
        </div>
      ) : (
        <svg
          width="100%"
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          preserveAspectRatio="none"
        >
          {latencies.map((ms, i) => {
            const x = i * (barW + gap);
            const h = Math.max(4, (ms / maxRef) * (height - 4));
            return (
              <rect
                key={i}
                x={x}
                y={height - h}
                width={barW}
                height={h}
                rx={3}
                fill={latencyColor(ms)}
                fillOpacity={0.5}
              />
            );
          })}
        </svg>
      )}
    </div>
  );
}
