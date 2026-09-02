import { useMemo } from 'react';
import EChart, { type EChartsOption } from '../shared/EChart';
import { useTranslation } from 'react-i18next';
import type { RetrievalLogItem } from '../../api/client/retrievalLogs';
import { axisLabelBase, axisLineBase, axisUnitName } from './chartAxis';
import { latencyColor, percentile } from './latency';

interface LatencyBarProps {
  items: RetrievalLogItem[];
}

export default function LatencyBar({ items }: LatencyBarProps) {
  const { t } = useTranslation();
  const latencies = items.map((i) => i.latencyMs);
  const p50 = percentile(latencies, 0.5);
  const p90 = percentile(latencies, 0.9);
  const max = latencies.length ? Math.max(...latencies) : 0;

  const option: EChartsOption = useMemo(() => {
    const pad = (n: number) => String(n).padStart(2, '0');
    const labels = items.map((i) => {
      const d = new Date(i.createdAt);
      return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
    });
    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: unknown) => {
          const p = params as Array<{ dataIndex: number; value: number }>;
          const item = items[p[0].dataIndex];
          return `<div style="font-weight:600">${item.query.slice(0, 40)}</div><div style="margin-top:4px">${labels[p[0].dataIndex]}：<b>${item.latencyMs}ms</b></div>`;
        },
      },
      grid: { left: 48, right: 16, top: 28, bottom: 24 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLabel: { ...axisLabelBase, hideOverlap: true },
        axisTick: { show: false },
        axisLine: axisLineBase.axisLine,
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { type: 'dashed' } },
        axisLabel: axisLabelBase,
        ...axisUnitName('ms'),
      },
      series: [
        {
          type: 'bar',
          data: items.map((i) => ({
            value: i.latencyMs,
            itemStyle: {
              color: latencyColor(i.latencyMs),
              borderRadius: [3, 3, 0, 0],
            },
          })),
          barWidth: '60%',
        },
      ],
    };
  }, [items]);

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
        <EChart
          option={option}
          height={140}
          ariaLabel={t('retrievalLogs.latencyTrend')}
          testId="latency-trend-chart"
        />
      )}
    </div>
  );
}
