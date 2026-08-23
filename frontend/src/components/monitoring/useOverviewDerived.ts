import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import type { MonitoringPoint } from '../../types/monitoring';
import { STATUS_COLORS } from '../shared/statusColors';
import type { EChartsOption } from '../shared/EChart';
import {
  lineTrendOption,
  volumeTrendOption,
  latencyTrendOption,
  periodDelta,
  withAlertMarks,
  withThresholdLine,
} from './chartOptions';

/** 与后端 max_empty_recall_pct 默认值一致（UI 未传自定义阈值）。 */
const EMPTY_RECALL_THRESHOLD_PCT = 15;

/** SLO 目标：95% 桶级 P95 ≤ 8s → 允许越线预算为 5%。 */
const SLO_TARGET_MISS_BUDGET_PCT = 5;

interface Params {
  points: MonitoringPoint[];
  prevPoints: MonitoringPoint[] | null;
  intraday: boolean;
}

/**
 * 总览面板的展示派生层：四张核心趋势图的 ECharts option
 * 与 SLO 达成率。数据获取在面板，图形编码在此，互不掺杂。
 */
export function useOverviewDerived({
  points,
  prevPoints,
  intraday,
}: Params) {
  const { t } = useTranslation();

  // 检索量图只承载流量语义：不叠加空召回告警点（与好评率图的同一条件标记重复）。
  const volumeChartOption: EChartsOption = useMemo(
    () =>
      volumeTrendOption({
        points,
        prevPoints,
        labels: {
          retrievals: t('monitoring.chartQualityLabel'),
          prevPeriod: t('monitoring.prevPeriod'),
        },
        intraday,
      }),
    [points, prevPoints, intraday, t],
  );

  const goodRateOf = (p: MonitoringPoint): number | null =>
    p.good + p.bad > 0 ? (p.good / (p.good + p.bad)) * 100 : null;
  const emptyRateOf = (p: MonitoringPoint): number | null =>
    p.retrievals > 0 ? (p.empty_count / p.retrievals) * 100 : null;

  // 好评率与空召回极性相反（一涨一跌为好），拆成两张 small multiples：
  // 各自独立 Y 轴刻度，避免共享 0-100% 轴造成的极性误读与量纲压缩。
  const goodRateChartOption: EChartsOption = useMemo(
    () =>
      lineTrendOption({
        points,
        prevPoints,
        pick: goodRateOf,
        color: STATUS_COLORS.green,
        labels: {
          series: t('monitoring.kpiGoodRate'),
          prevPeriod: t('monitoring.prevPeriod'),
        },
        formatValue: (v) => `${v.toFixed(1)}%`,
        intraday,
      }),
    [points, prevPoints, intraday, t],
  );

  // Y 上界取 max(阈值×1.5, 观测峰值向上取整)，保证警戒线不越出绘图区。
  const emptyRecallMax = useMemo(() => {
    const observed = points
      .map(emptyRateOf)
      .filter((v): v is number => v != null);
    const peak = observed.length > 0 ? Math.max(...observed) : 0;
    return Math.ceil(Math.max(15 * 1.5, peak * 1.1) / 5) * 5;
  }, [points]);

  // 柱状编码：空召回是"逐桶对照阈值判定"的离散指标；警戒线 + 越线红点组合，
  // 回答"现在超没超、何时超的"两个问题。
  const emptyRecallChartOption: EChartsOption = useMemo(
    () =>
      withAlertMarks(
        withThresholdLine(
          lineTrendOption({
            points,
            pick: emptyRateOf,
            color: STATUS_COLORS.amber,
            labels: {
              series: t('monitoring.retrieval.emptyRecall'),
              prevPeriod: t('monitoring.prevPeriod'),
            },
            formatValue: (v) => `${v.toFixed(1)}%`,
            intraday,
            yAxisMin: 0,
            yAxisMax: emptyRecallMax,
            asBars: true,
          }),
          t('monitoring.retrieval.emptyRecall'),
          {
            yAxis: EMPTY_RECALL_THRESHOLD_PCT,
            label: `${t('monitoring.chartThreshold')} ${EMPTY_RECALL_THRESHOLD_PCT}%`,
          },
        ),
        points,
        {
          targetSeriesName: t('monitoring.retrieval.emptyRecall'),
          valueAt: emptyRateOf,
          breached: (p) => {
            const rate = emptyRateOf(p);
            return rate != null && rate > EMPTY_RECALL_THRESHOLD_PCT;
          },
          label: t('monitoring.alerts.breach'),
        },
      ),
    [points, intraday, emptyRecallMax, t],
  );

  const latencyChartOption: EChartsOption = useMemo(
    () =>
      withAlertMarks(
        latencyTrendOption({
          points,
          p95ThresholdMs: 8000,
          labels: {
            avgLatency: t('monitoring.kpiAvgLatency'),
            bandLabel: 'P50–P95',
            p99Label: t('monitoring.retrieval.p99'),
            threshold: t('monitoring.chartThreshold'),
          },
          intraday,
        }),
        points,
        {
          targetSeriesName: '__band_top',
          valueAt: (p) => p.latency_p95_ms,
          breached: (p) => p.latency_p95_ms != null && p.latency_p95_ms > 8000,
          label: t('monitoring.alerts.breach'),
        },
      ),
    [points, intraday, t],
  );

  // SLO 达成率：窗口内有样本的桶中，桶级 P95 ≤ 8000ms 的占比。
  const sloPct = useMemo(() => {
    const sampled = points.filter((p) => p.latency_p95_ms != null);
    if (sampled.length === 0) return null;
    const met = sampled.filter((p) => (p.latency_p95_ms as number) <= 8000).length;
    return Math.round((met / sampled.length) * 100);
  }, [points]);

  // 错误预算燃烧率（Google SRE）：SLO 目标 95%，预算即 5% 越线配额。
  // burn = 实际越线比例 ÷ 预算；≥1× 表示预算消耗速度超标，需介入。
  const sloBurnRate = useMemo(() => {
    if (sloPct == null || sloPct >= 100) return null;
    return Math.round(((100 - sloPct) / SLO_TARGET_MISS_BUDGET_PCT) * 100) / 100;
  }, [sloPct]);

  // 周期环比：当前窗口 vs 后端返回的对齐上期（预设窗口才有）。
  const totalDelta = useMemo(
    () =>
      periodDelta(
        points.map((p) => p.retrievals),
        prevPoints?.map((p) => p.retrievals) ?? [],
        'sum',
      ),
    [points, prevPoints],
  );
  const emptyRecallDelta = useMemo(
    () =>
      periodDelta(
        points.map((p) => emptyRateOf(p) ?? 0),
        prevPoints?.map((p) => emptyRateOf(p) ?? 0) ?? [],
        'avg',
      ),
    [points, prevPoints],
  );
  const goodRateDelta = useMemo(
    () =>
      periodDelta(
        points.map((p) => goodRateOf(p) ?? 0),
        prevPoints?.map((p) => goodRateOf(p) ?? 0) ?? [],
        'avg',
      ),
    [points, prevPoints],
  );
  const latDelta = useMemo(
    () =>
      periodDelta(
        points.map((p) => p.avg_latency_ms ?? 0),
        prevPoints?.map((p) => p.avg_latency_ms ?? 0) ?? [],
        'avg',
      ),
    [points, prevPoints],
  );

  return {
    volumeChartOption,
    goodRateChartOption,
    emptyRecallChartOption,
    latencyChartOption,
    totalDelta,
    emptyRecallDelta,
    goodRateDelta,
    latDelta,
    sloPct,
    sloBurnRate,
  };
}
