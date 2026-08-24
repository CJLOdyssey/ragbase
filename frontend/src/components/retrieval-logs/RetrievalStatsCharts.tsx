import { useMemo } from 'react';
import EChart, { type EChartsOption } from '../shared/EChart';
import { STATUS_COLORS } from '../shared/statusColors';
import { useTranslation } from 'react-i18next';
import type { RetrievalStatsResponse } from '../../api/client/retrievalLogs';
import {
  axisLabelBase,
  axisLineBase,
  axisUnitName,
  HEAT_RAMP,
} from './chartAxis';
import { LATENCY_GREEN, LATENCY_RED } from './latency';

interface Props {
  stats: RetrievalStatsResponse;
  /** 当前时间窗口标签（近24小时/近72小时/近7天/全部/自定义区间），用于趋势图标题。 */
  rangeLabel: string;
}

function LatencyBarChart({ stats }: { stats: RetrievalStatsResponse }) {
  const { t } = useTranslation();
  const option: EChartsOption = useMemo(() => {
    const buckets = stats.latencyDistribution;
    const ranges = ['<150ms', '150-300ms', '>300ms'];
    const colorMap: Record<string, string> = {
      '<150ms': LATENCY_GREEN,
      '150-300ms': STATUS_COLORS.amber,
      '>300ms': LATENCY_RED,
    };
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 40, right: 16, top: 30, bottom: 24 },
      xAxis: {
        type: 'category',
        data: ranges,
        axisTick: { show: false },
        axisLine: axisLineBase.axisLine,
        axisLabel: axisLabelBase,
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { type: 'dashed' } },
        axisLabel: axisLabelBase,
        ...axisUnitName(t('retrievalLogs.unit.count')),
      },
      series: [
        {
          type: 'bar',
          data: ranges.map((r) => {
            const found = buckets.find((b) => b.range === r);
            return {
              value: found?.count ?? 0,
              itemStyle: { color: colorMap[r], borderRadius: [3, 3, 0, 0] },
            };
          }),
          barWidth: '50%',
        },
      ],
    };
  }, [stats, t]);

  return (
    <EChart
      option={option}
      height={160}
      ariaLabel={t('retrievalLogs.latencyDistribution')}
      testId="latency-bar-chart"
    />
  );
}

function HitRatePieChart({ stats }: { stats: RetrievalStatsResponse }) {
  const { t } = useTranslation();
  const option: EChartsOption = useMemo(() => {
    const { hitRate } = stats;
    return {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { show: false },
      series: [
        {
          type: 'pie',
          radius: ['45%', '70%'],
          avoidLabelOverlap: false,
          label: { show: false },
          emphasis: {
            label: { show: true, fontSize: 14, fontWeight: 'bold' },
          },
          data: [
            {
              value: hitRate.hitRecall,
              name: t('retrievalLogs.hitRecall'),
              itemStyle: { color: LATENCY_GREEN },
            },
            {
              value: hitRate.emptyRecall,
              name: t('retrievalLogs.emptyRecall'),
              itemStyle: { color: LATENCY_RED },
            },
          ],
        },
      ],
    };
  }, [stats, t]);

  return (
    <EChart
      option={option}
      height={160}
      ariaLabel={t('retrievalLogs.hitRate')}
      testId="hit-rate-pie-chart"
    />
  );
}

function QueryTrendChart({
  stats,
  rangeLabel,
}: {
  stats: RetrievalStatsResponse;
  rangeLabel: string;
}) {
  const { t } = useTranslation();
  const option: EChartsOption = useMemo(() => {
    const { volumeTrend } = stats;
    const pad = (n: number) => String(n).padStart(2, '0');
    const fmt = (ts: string, withDate: boolean) => {
      const d = new Date(ts);
      return withDate
        ? `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
        : `${pad(d.getHours())}:${pad(d.getMinutes())}`;
    };
    const first = volumeTrend[0]?.ts;
    const last = volumeTrend[volumeTrend.length - 1]?.ts;
    // ≤24h 窗口用 HH:mm，跨天必须带日期否则无法区分桶。
    const intraday =
      !!first && !!last && +new Date(last) - +new Date(first) <= 24 * 3600_000;
    const labels = volumeTrend.map((p) => fmt(p.ts, !intraday));
    return {
      tooltip: {
        trigger: 'axis',
        formatter: (params: unknown) => {
          const list = params as Array<{ dataIndex: number }>;
          const p = volumeTrend[list[0].dataIndex];
          return `<div style="font-weight:600">${fmt(p.ts, true)}</div><div style="margin-top:4px">${t('retrievalLogs.unit.count')}：<b>${p.count}</b></div>`;
        },
      },
      grid: { left: 40, right: 16, top: 30, bottom: 24 },
      // 图表内缩放（ECharts 官方推荐交互）：滚轮缩放 / 拖拽平移，无滑条。
      dataZoom: [{ type: 'inside', zoomOnMouseWheel: true }],
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
        ...axisUnitName(t('retrievalLogs.unit.count')),
      },
      series: [
        {
          type: 'line',
          data: volumeTrend.map((p) => p.count),
          smooth: true,
          symbol: 'circle',
          symbolSize: 4,
          lineStyle: { color: STATUS_COLORS.blue, width: 2 },
          itemStyle: { color: STATUS_COLORS.blue },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(59,130,246,0.3)' },
                { offset: 1, color: 'rgba(59,130,246,0.02)' },
              ],
            },
          },
        },
      ],
    };
  }, [stats, t]);

  return (
    <EChart
      option={option}
      height={160}
      ariaLabel={t('retrievalLogs.queryTrend', { range: rangeLabel })}
      testId="query-trend-chart"
    />
  );
}

function ActivityHeatmapChart({ stats }: { stats: RetrievalStatsResponse }) {
  const { t } = useTranslation();
  const option: EChartsOption = useMemo(() => {
    const { dailyActivity } = stats;
    const days = [
      t('retrievalLogs.daySun'),
      t('retrievalLogs.dayMon'),
      t('retrievalLogs.dayTue'),
      t('retrievalLogs.dayWed'),
      t('retrievalLogs.dayThu'),
      t('retrievalLogs.dayFri'),
      t('retrievalLogs.daySat'),
    ];
    const hours = Array.from({ length: 24 }, (_, i) => `${i}`);
    const data: [number, number, number][] = dailyActivity.map((d) => [
      d.hour,
      d.day,
      d.count,
    ]);
    const maxCount = Math.max(...data.map((d) => d[2]), 1);

    return {
      tooltip: {
        position: 'top',
      },
      grid: { left: 40, right: 16, top: 8, bottom: 32 },
      xAxis: {
        type: 'category',
        data: hours,
        axisLabel: {
          interval: 5,
          ...axisLabelBase,
          formatter: (v: string) => `${v}${t('retrievalLogs.unit.hour')}`,
        },
        axisTick: { show: false },
        axisLine: axisLineBase.axisLine,
      },
      yAxis: {
        type: 'category',
        data: days,
        axisLabel: { ...axisLabelBase },
        axisTick: { show: false },
        axisLine: axisLineBase.axisLine,
      },
      visualMap: {
        min: 0,
        max: maxCount,
        calculable: false,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        inRange: {
          color: HEAT_RAMP,
        },
        show: false,
      },
      series: [
        {
          type: 'heatmap',
          data,
          label: { show: false },
          emphasis: {
            itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0,0,0,0.3)' },
          },
        },
      ],
    };
  }, [stats, t]);

  return (
    <EChart
      option={option}
      height={160}
      ariaLabel={t('retrievalLogs.activityHeatmap')}
      testId="activity-heatmap-chart"
    />
  );
}

export default function RetrievalStatsCharts({ stats, rangeLabel }: Props) {
  const { t } = useTranslation();
  const { hitRate } = stats;

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-4">
          <div className="text-xs font-medium text-[var(--color-text-muted)] mb-2">
            {t('retrievalLogs.latencyDistribution')}
          </div>
          <LatencyBarChart stats={stats} />
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-4">
          <div className="text-xs font-medium text-[var(--color-text-muted)] mb-2">
            {t('retrievalLogs.hitRate')}
          </div>
          <div className="flex items-center justify-center">
            <HitRatePieChart stats={stats} />
          </div>
          <div className="text-center text-xs text-[var(--color-text-secondary)] mt-1">
            {hitRate.total > 0
              ? `${t('retrievalLogs.emptyRecallRate')}: ${hitRate.emptyRecallRate}%`
              : '—'}
          </div>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-4 lg:col-span-2">
          <div className="text-xs font-medium text-[var(--color-text-muted)] mb-2">
            {t('retrievalLogs.queryTrend', { range: rangeLabel })}
          </div>
          <QueryTrendChart stats={stats} rangeLabel={rangeLabel} />
        </div>
      </div>
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-4">
        <div className="text-xs font-medium text-[var(--color-text-muted)] mb-2">
          {t('retrievalLogs.activityHeatmap')}
        </div>
        <ActivityHeatmapChart stats={stats} />
      </div>
    </div>
  );
}
