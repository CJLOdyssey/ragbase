import type { MonitoringPoint } from '../../../types/monitoring';
import type { EChartsOption } from '../../shared/EChart';
import {
  ACCENT,
  alignedGhost,
  axisTooltip,
  compact,
  DANGER,
  ghostSeries,
  GRID_TEXT,
  hexA,
  legendStyle,
  MUTED_TEXT,
  spansYear,
  SUCCESS,
  timeAxis,
  tooltipTime,
  type SeriesFmtMap,
} from './shared';

// ── KPI 环比 delta ──────────────────────────────────────────────────────────

export interface KpiDelta {
  /** 当前周期相对上一同等周期的变化百分比（有符号）。 */
  pct: number;
  /** true = 本期更高。 */
  up: boolean;
}

/**
 * 总量类指标的周期环比（sum）：当前窗口 vs 紧邻的上一同等周期。
 * 上期无基线（空/零/非有限值）→ null，不展示涨跌。
 */
export function periodDelta(
  current: number[],
  previous: number[],
): KpiDelta | null {
  const clean = previous.filter((v) => Number.isFinite(v));
  const prev = clean.reduce((a, b) => a + b, 0);
  if (current.length === 0 || clean.length === 0 || prev <= 0) return null;
  const cur = current.reduce((a, b) => a + b, 0);
  return { pct: ((cur - prev) / prev) * 100, up: cur >= prev };
}

/**
 * 比率型指标的周期环比：分子/分母分别跨桶加总后相除（ratio-of-sums，
 * Prometheus 官方推荐的比率聚合方式）。无样本的桶自然退出分母，
 * 杜绝"等权平均被零样本桶稀释"的失真。上期分母无正基线 → null。
 */
export function ratioDelta(
  curNum: Array<number | null>,
  curDen: Array<number | null>,
  prevNum: Array<number | null>,
  prevDen: Array<number | null>,
): KpiDelta | null {
  const sum = (xs: Array<number | null>) =>
    xs.reduce<number>(
      (acc, v) => (Number.isFinite(v) ? acc + (v as number) : acc),
      0,
    );
  const curD = sum(curDen);
  const prevD = sum(prevDen);
  if (!(curD > 0) || !(prevD > 0)) return null;
  const cur = sum(curNum) / curD;
  const prev = sum(prevNum) / prevD;
  return { pct: ((cur - prev) / prev) * 100, up: cur >= prev };
}

/**
 * 均值型指标的周期环比：以样本量加权（如按检索次数），稀疏桶不再扭曲整体均值。
 * 非有限值或权重 ≤0 的桶剔除；任一侧无有效样本或上期基线 ≤0 → null。
 */
export function weightedDelta(
  curVals: Array<number | null>,
  curWeights: Array<number | null>,
  prevVals: Array<number | null>,
  prevWeights: Array<number | null>,
): KpiDelta | null {
  const wmean = (
    vals: Array<number | null>,
    weights: Array<number | null>,
  ): number | null => {
    let num = 0;
    let den = 0;
    for (let i = 0; i < vals.length; i += 1) {
      const v = vals[i];
      const w = weights[i];
      if (!Number.isFinite(v) || !Number.isFinite(w) || (w as number) <= 0)
        continue;
      num += (v as number) * (w as number);
      den += w as number;
    }
    return den > 0 ? num / den : null;
  };
  const cur = wmean(curVals, curWeights);
  const prev = wmean(prevVals, prevWeights);
  if (cur === null || prev === null || prev <= 0) return null;
  return { pct: ((cur - prev) / prev) * 100, up: cur >= prev };
}

// ── 柱状趋势（检索量）───────────────────────────────────────────────────────

export interface VolumeTrendSpec {
  points: MonitoringPoint[];
  prevPoints?: MonitoringPoint[] | null;
  labels: { retrievals: string; prevPeriod: string };
  intraday: boolean;
}

/** 检索量趋势：柱（左轴·次）+ 可选上期 ghost 虚线。 */
export function volumeTrendOption(spec: VolumeTrendSpec): EChartsOption {
  const { points, prevPoints, labels, intraday } = spec;
  const includeYear = spansYear(points);
  const volumes = points.map((p) => [p.ts, p.retrievals] as [string, number]);
  const ghost = ghostSeries(
    alignedGhost(points, prevPoints, (p) => p.retrievals),
    labels.prevPeriod,
  );

  const fmts: SeriesFmtMap = new Map([
    [labels.retrievals, (v) => compact(v)],
    [labels.prevPeriod, (v) => compact(v)],
  ]);

  return {
    grid: { left: 44, right: 18, top: 30, bottom: 26 },
    legend: ghost ? legendStyle : undefined,
    tooltip: axisTooltip(fmts, includeYear),
    xAxis: timeAxis(intraday, includeYear),
    yAxis: {
      type: 'value',
      splitNumber: 3,
      splitLine: { lineStyle: { color: GRID_TEXT, type: 'dashed' } },
      axisLabel: { color: MUTED_TEXT, fontSize: 10, formatter: compact },
    },
    series: [
      ...(ghost ? [ghost] : []),
      {
        name: labels.retrievals,
        type: 'bar',
        data: volumes,
        barMaxWidth: 14,
        itemStyle: { color: hexA(ACCENT, 0.55) },
        z: 3,
      },
    ],
  };
}

// ── 单序列趋势小图（small multiples）───────────────────────────────────────

export interface LineTrendSpec {
  points: MonitoringPoint[];
  prevPoints?: MonitoringPoint[] | null;
  pick: (p: MonitoringPoint) => number | null;
  color: string;
  labels: { series: string; prevPeriod: string };
  formatValue: (v: number) => string;
  intraday: boolean;
  yAxisMin?: number;
  yAxisMax?: number;
  asBars?: boolean;
}

/** 单序列趋势小图：一图一量纲 + 可选上期虚线。 */
export function lineTrendOption(spec: LineTrendSpec): EChartsOption {
  const { points, prevPoints, pick, color, labels, formatValue, intraday } =
    spec;
  const includeYear = spansYear(points);
  const data = points.map((p) => [p.ts, pick(p)] as [string, number | null]);
  const ghost = ghostSeries(
    alignedGhost(points, prevPoints, pick),
    labels.prevPeriod,
  );

  const fmts: SeriesFmtMap = new Map([
    [labels.series, formatValue],
    [labels.prevPeriod, formatValue],
  ]);

  return {
    grid: { left: 44, right: 18, top: 30, bottom: 26 },
    legend: ghost ? legendStyle : undefined,
    tooltip: axisTooltip(fmts, includeYear),
    xAxis: timeAxis(intraday, includeYear),
    yAxis: {
      type: 'value',
      scale: true,
      min: spec.yAxisMin,
      max: spec.yAxisMax,
      splitNumber: 3,
      splitLine: { lineStyle: { color: GRID_TEXT, type: 'dashed' } },
      axisLabel: { color: MUTED_TEXT, fontSize: 10, formatter: compact },
    },
    series: [
      ...(ghost ? [ghost] : []),
      spec.asBars
        ? {
            name: labels.series,
            type: 'bar',
            data,
            barMaxWidth: 12,
            z: 3,
            itemStyle: { color: hexA(color, 0.75) },
          }
        : {
            name: labels.series,
            type: 'line',
            data,
            smooth: 0.3,
            showSymbol: points.length <= 24,
            symbolSize: 5,
            connectNulls: false,
            z: 3,
            lineStyle: { width: 1.5, color },
            itemStyle: { color },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: hexA(color, 0.14) },
                  { offset: 1, color: hexA(color, 0) },
                ],
              },
            },
          },
    ],
  };
}

// ── 延迟分位数带图（双层带：P50–P95 / P95–P99）─────────────────────────────

export interface LatencyTrendSpec {
  points: MonitoringPoint[];
  p95ThresholdMs: number;
  labels: {
    avgLatency: string;
    bandLabel: string;
    p99Label: string;
    threshold: string;
  };
  intraday: boolean;
}

/**
 * 延迟分位数带图（Datadog 式双层带）：P50–P95 主带（accent）+
 * P95–P99 极端尾部带（danger 淡染）+ 均值线 + SLO 阈值警戒线。
 */
export function latencyTrendOption(spec: LatencyTrendSpec): EChartsOption {
  const { points, p95ThresholdMs, labels, intraday } = spec;

  const p95Data: Array<[string, number | null]> = [];
  const bandDelta: Array<[string, number | null]> = [];
  const p99Data: Array<[string, number | null]> = [];
  const tailDelta: Array<[string, number | null]> = [];
  const avgData: Array<[string, number | null]> = [];
  const rowByTs = new Map<string, MonitoringPoint>();
  for (const p of points) {
    rowByTs.set(p.ts, p);
    if (p.latency_p95_ms != null && p.latency_p50_ms != null) {
      p95Data.push([p.ts, p.latency_p95_ms]);
      bandDelta.push([p.ts, p.latency_p50_ms - p.latency_p95_ms]);
    } else {
      p95Data.push([p.ts, null]);
      bandDelta.push([p.ts, null]);
    }
    if (p.latency_p99_ms != null && p.latency_p95_ms != null) {
      p99Data.push([p.ts, p.latency_p99_ms]);
      tailDelta.push([p.ts, p.latency_p95_ms - p.latency_p99_ms]);
    } else {
      p99Data.push([p.ts, null]);
      tailDelta.push([p.ts, null]);
    }
    avgData.push([p.ts, p.avg_latency_ms]);
  }

  return {
    grid: { left: 46, right: 18, top: 34, bottom: 26 },
    tooltip: {
      ...axisTooltip(new Map(), spansYear(points)),
      formatter: (params: unknown) => {
        const list = params as Array<{
          seriesName?: string;
          value: [string, number | null];
        }>;
        if (!list.length) return '';
        const ts = list[0].value[0];
        const p = rowByTs.get(ts);
        const time = tooltipTime(ts, spansYear(points));
        if (!p) return `<div style="font-weight:600">${time}</div>`;
        const rows: Array<{ name: string; v: number | null; color: string }> = [
          { name: labels.p99Label, v: p.latency_p99_ms, color: DANGER },
          { name: labels.bandLabel, v: p.latency_p95_ms, color: ACCENT },
          { name: labels.avgLatency, v: p.avg_latency_ms, color: SUCCESS },
        ];
        const body = rows
          .map(
            ({ name, v, color }) =>
              `<div style="margin-top:4px"><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${color};margin-right:6px"></span>${name}：<b>${
                v == null ? '—' : `${Math.round(v)}ms`
              }</b></div>`,
          )
          .join('');
        return `<div style="font-weight:600">${time}</div>${body}`;
      },
    },
    xAxis: timeAxis(intraday, spansYear(points)),
    yAxis: {
      type: 'value',
      splitNumber: 3,
      scale: true,
      splitLine: { lineStyle: { color: GRID_TEXT, type: 'dashed' } },
      axisLabel: { color: MUTED_TEXT, fontSize: 10, formatter: compact },
    },
    series: [
      {
        name: '__band_top',
        type: 'line',
        data: p95Data,
        stack: 'latency-core',
        lineStyle: { opacity: 0 },
        symbol: 'none',
        silent: true,
        connectNulls: false,
      },
      {
        name: labels.bandLabel,
        type: 'line',
        data: bandDelta,
        stack: 'latency-core',
        lineStyle: { opacity: 0 },
        symbol: 'none',
        silent: true,
        connectNulls: false,
        areaStyle: { color: hexA(ACCENT, 0.16) },
      },
      {
        name: '__band_top_p99',
        type: 'line',
        data: p99Data,
        stack: 'latency-tail',
        lineStyle: { opacity: 0 },
        symbol: 'none',
        silent: true,
        connectNulls: false,
      },
      {
        name: labels.p99Label,
        type: 'line',
        data: tailDelta,
        stack: 'latency-tail',
        lineStyle: { opacity: 0 },
        symbol: 'none',
        silent: true,
        connectNulls: false,
        areaStyle: { color: hexA(DANGER, 0.1) },
      },
      {
        name: labels.avgLatency,
        type: 'line',
        data: avgData,
        smooth: 0.25,
        showSymbol: false,
        connectNulls: false,
        lineStyle: { width: 1.5, color: SUCCESS },
        itemStyle: { color: SUCCESS },
        markLine: {
          silent: true,
          symbol: 'none',
          data: [
            {
              yAxis: p95ThresholdMs,
              lineStyle: {
                color: hexA(DANGER, 0.35),
                type: 'dashed',
                width: 1,
              },
              label: {
                formatter: `${labels.threshold} ${compact(p95ThresholdMs)}ms`,
                position: 'insideEndBottom',
                color: DANGER,
                fontSize: 10,
              },
            },
          ],
        },
      },
    ],
  };
}
