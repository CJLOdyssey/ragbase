import type { EChartsOption } from '../shared/EChart';
import type { MonitoringPoint } from '../../types/monitoring';

/** #rrggbb → rgba(r,g,b,a)，渐变与指示线同源配色。 */
export function hexA(hex: string, alpha: number): string {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// 与 styles/tailwind-entry.css 的语义 token 保持同源，禁止体系外默认色。
const ACCENT = '#6366f1'; // --color-accent
const SUCCESS = '#34d399'; // --color-success
const WARNING = '#f59e0b'; // --color-warning
const DANGER = '#ff4444'; // --color-danger
const MUTED_TEXT = '#8a8f98';
const GRID_TEXT = 'rgba(138,143,152,0.14)';

const compact = (n: number): string => {
  const abs = Math.abs(n);
  const units: Array<[number, string]> = [
    [1e9, 'B'],
    [1e6, 'M'],
    [1e3, 'k'],
  ];
  for (const [size, suffix] of units) {
    if (abs >= size) {
      const v = n / size;
      // 大数少留小数位，避免 "1500.0k" 这类冗长刻度。
      const scaled = abs / size;
      const text = scaled >= 100 ? v.toFixed(0) : v.toFixed(1);
      return `${text.replace(/\.0$/, '')}${suffix}`;
    }
  }
  return Number.isInteger(n) ? String(n) : abs >= 10 ? n.toFixed(0) : n.toFixed(1);
};

/** 跨自然年或超半年的窗口，时间标签需带年份否则无法区分。 */
function spansAcrossYear(firstTs: number, lastTs: number): boolean {
  const a = new Date(firstTs);
  const b = new Date(lastTs);
  return (
    a.getFullYear() !== b.getFullYear() ||
    b.getTime() - a.getTime() > 180 * 86400_000
  );
}

export interface KpiDelta {
  /** 当前周期相对上一同等周期的变化百分比（有符号）。 */
  pct: number;
  /** true = 本期更高。 */
  up: boolean;
}

/**
 * 真·周期环比：当前窗口 vs 紧邻的上一同等周期。
 * 上期无基线（空/零/非有限值）→ null，不展示涨跌。
 */
export function periodDelta(
  current: number[],
  previous: number[],
  mode: 'sum' | 'avg',
): KpiDelta | null {
  const agg = (values: number[]) => {
    const clean = values.filter((v) => Number.isFinite(v));
    if (clean.length === 0) return null;
    return mode === 'sum'
      ? clean.reduce((a, b) => a + b, 0)
      : clean.reduce((a, b) => a + b, 0) / clean.length;
  };
  const cur = agg(current);
  const prev = agg(previous);
  if (cur === null || prev === null || prev <= 0) return null;
  return { pct: ((cur - prev) / prev) * 100, up: cur >= prev };
}

function timeAxis(intraday: boolean, includeYear: boolean) {
  return {
    type: 'time' as const,
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: {
      color: MUTED_TEXT,
      fontSize: 10,
      hideOverlap: true,
      formatter: (ts: number) => {
        const d = new Date(ts);
        const pad = (n: number) => String(n).padStart(2, '0');
        if (includeYear) return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
        return intraday
          ? `${pad(d.getHours())}:${pad(d.getMinutes())}`
          : `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
      },
    },
  };
}

function tooltipTime(tsMs: number | string, includeYear: boolean): string {
  const d = new Date(tsMs);
  const pad = (n: number) => String(n).padStart(2, '0');
  const date = includeYear
    ? `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
    : `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  return `${date} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

type SeriesFmtMap = Map<string, (v: number) => string>;

function axisTooltip(fmts: SeriesFmtMap, includeYear: boolean) {
  return {
    trigger: 'axis' as const,
    axisPointer: {
      type: 'line' as const,
      lineStyle: { color: 'rgba(138,143,152,0.35)', width: 1 },
    },
    backgroundColor: 'rgba(17,21,28,0.96)',
    borderColor: 'rgba(255,255,255,0.08)',
    borderWidth: 1,
    padding: [8, 12],
    textStyle: { color: '#e6e9ef', fontSize: 12 },
    formatter: (params: unknown) => {
      const list = params as Array<{
        seriesName: string;
        value: [string, number | null];
        color?: string;
      }>;
      if (!list.length) return '';
      const time = tooltipTime(list[0].value[0], includeYear);
      const rows = list
        .map((p) => {
          const raw = p.value[1];
          const shown =
            raw === null || raw === undefined
              ? '—'
              : (fmts.get(p.seriesName) ?? compact)(raw);
          return `<div style="margin-top:4px"><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${p.color ?? MUTED_TEXT};margin-right:6px"></span>${p.seriesName}：<b>${shown}</b></div>`;
        })
        .join('');
      return `<div style="font-weight:600">${time}</div>${rows}`;
    },
  };
}

const legendStyle = {
  top: 0,
  right: 0,
  icon: 'roundRect' as const,
  itemWidth: 10,
  itemHeight: 6,
  textStyle: { color: MUTED_TEXT, fontSize: 10 },
};

/**
 * 上期序列按 index 对齐到本期时间戳 —— ghost 虚线与真·环比共用此对齐。
 * 长度不一致时返回 undefined（宁缺毋错位）。
 */
export function alignedGhost(
  points: MonitoringPoint[],
  prevPoints: MonitoringPoint[] | null | undefined,
  pick: (p: MonitoringPoint) => number | null,
): Array<[string, number | null]> | undefined {
  if (!prevPoints || prevPoints.length !== points.length) return undefined;
  return points.map(
    (p, i) => [p.ts, pick(prevPoints[i])] as [string, number | null],
  );
}

const GHOST_STYLE = {
  width: 1,
  type: 'dashed' as const,
  color: 'rgba(138,143,152,0.45)',
};

function ghostSeries(
  data: Array<[string, number | null]> | undefined,
  name: string,
) {
  if (!data) return null;
  return {
    name,
    type: 'line' as const,
    data,
    smooth: 0.25,
    showSymbol: false,
    connectNulls: false,
    silent: true,
    lineStyle: GHOST_STYLE,
    itemStyle: { color: GHOST_STYLE.color },
  };
}

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

export interface LineTrendSpec {
  points: MonitoringPoint[];
  prevPoints?: MonitoringPoint[] | null;
  pick: (p: MonitoringPoint) => number | null;
  color: string;
  labels: { series: string; prevPeriod: string };
  formatValue: (v: number) => string;
  intraday: boolean;
  /** 可选 Y 轴下界（如比率图固定 0 基线）。 */
  yAxisMin?: number;
  /** 可选 Y 轴上界（如需为阈值警戒线预留空间）。 */
  yAxisMax?: number;
  /**
   * 柱状变体：语义为"逐桶对照阈值判定"的离散指标
   * （如空召回率），柱比平滑线更贴近检查心智。
   */
  asBars?: boolean;
}

/** 单序列趋势小图（small multiples）：一图一量纲 + 可选上期虚线。 */
export function lineTrendOption(spec: LineTrendSpec): EChartsOption {
  const { points, prevPoints, pick, color, labels, formatValue, intraday } =
    spec;
  const includeYear = spansYear(points);
  const data = points.map((p) => [p.ts, pick(p)] as [string, number | null]);
  const ghost = ghostSeries(alignedGhost(points, prevPoints, pick), labels.prevPeriod);

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

export interface LatencyTrendSpec {
  points: MonitoringPoint[];
  /** 与后端 max_p95_latency_ms 默认值一致。 */
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
 * 内带 = 大多数请求的形态；外带 = 长尾恶化最先显形的位置。
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
      // 负偏移叠在 p95 之上，面积即 p50–p95 区间。
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
      ...axisTooltip(new Map(), includeYearOf(points)),
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
    xAxis: timeAxis(intraday, includeYearOf(points)),
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
        // 中性 accent：带宽只表达尾部形态，宽 ≠ 坏，避免 SUCCESS 绿误导。
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
        // 极端尾部淡染：p95→p99 越宽，最慢 1% 用户越痛苦。
        areaStyle: { color: hexA(DANGER, 0.10) },
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
              lineStyle: { color: hexA(DANGER, 0.35), type: 'dashed', width: 1 },
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

function spansYear(points: MonitoringPoint[]): boolean {
  return (
    points.length > 1 &&
    spansAcrossYear(+new Date(points[0].ts), +new Date(points[points.length - 1].ts))
  );
}

function includeYearOf(points: MonitoringPoint[]): boolean {
  return spansYear(points);
}

// ---------------------------------------------------------------------------
// 分布与诊断层 builders：漏斗 / 根因帕累托 / 健康分仪表。
// ---------------------------------------------------------------------------

export interface FunnelStage {
  name: string;
  value: number;
}

/** 检索转化漏斗：总检索 → 有命中 → 已评价 → 好评，逐级收窄即漏损。 */
export function retrievalFunnelOption(spec: {
  stages: FunnelStage[];
}): EChartsOption {
  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(17,21,28,0.96)',
      borderColor: 'rgba(255,255,255,0.08)',
      borderWidth: 1,
      padding: [6, 10],
      textStyle: { color: '#e6e9ef', fontSize: 11 },
    },
    series: [
      {
        type: 'funnel',
        left: '8%',
        right: '8%',
        top: 4,
        bottom: 4,
        minSize: '32%',
        sort: 'descending',
        gap: 2,
        label: {
          show: true,
          position: 'inside',
          fontSize: 12,
          color: '#0b0d12',
          // 名称 + 绝对值 + 相对上级的逐级转化率（首级为基准 100%）。
          formatter: (params: unknown) => {
            const p = params as { dataIndex?: number };
            const i = p.dataIndex ?? 0;
            const stage = spec.stages[i];
            if (!stage) return '';
            const prev = i > 0 ? spec.stages[i - 1].value : null;
            const pct =
              prev != null && prev > 0
                ? Math.round((stage.value / prev) * 1000) / 10
                : 100;
            return `${stage.name}\u3000${stage.value}\n${pct}%`;
          },
        },
        itemStyle: { borderColor: 'transparent', borderWidth: 0 },
        data: spec.stages.map((stage, i) => ({
          ...stage,
          itemStyle: {
            color: hexA(ACCENT, Math.max(0.3, 0.9 - i * 0.18)),
          },
        })),
        emphasis: { disabled: true },
      },
    ],
  };
}

export interface RootCauseParetoSpec {
  /** 类目名（按计数降序）；横向条形图 inverse 轴 → 首项渲染在顶部。 */
  categories: string[];
  counts: number[];
  /** 累计占比（%），与 categories 等长。 */
  cumulativePct: number[];
  labels: { count: string; cumulative: string };
}

/**
 * 差评根因帕累托：横向条形（左轴·次数）+ 累计占比线（上轴·%）。
 * 前几类条形越长 → 修复杠杆越大。
 */
export function rootCauseParetoOption(spec: RootCauseParetoSpec): EChartsOption {
  const { categories, counts, cumulativePct, labels } = spec;
  const fmts: SeriesFmtMap = new Map([
    [labels.count, (v) => compact(v)],
    [labels.cumulative, (v) => `${v.toFixed(1)}%`],
  ]);
  return {
    grid: { left: 84, right: 22, top: 32, bottom: 28 },
    tooltip: axisTooltip(fmts, false),
    xAxis: [
      {
        type: 'value',
        splitNumber: 2,
        splitLine: { show: false },
        axisLabel: { show: false },
      },
      {
        type: 'value',
        min: 0,
        max: 100,
        splitNumber: 2,
        splitLine: { show: false },
        axisLabel: {
          color: MUTED_TEXT,
          fontSize: 10,
          formatter: '{value}%',
        },
      },
    ],
    yAxis: {
      type: 'category',
      data: categories,
      inverse: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: MUTED_TEXT, fontSize: 11 },
    },
    legend: legendStyle,
    series: [
      {
        name: labels.count,
        type: 'bar',
        data: counts,
        barMaxWidth: 16,
        itemStyle: { color: hexA(ACCENT, 0.75), borderRadius: [0, 3, 3, 0] },
        label: {
          show: true,
          position: 'right',
          fontSize: 11,
          color: MUTED_TEXT,
        },
      },
      {
        name: labels.cumulative,
        type: 'line',
        xAxisIndex: 1,
        smooth: 0.3,
        symbolSize: 6,
        data: cumulativePct,
        lineStyle: { width: 1.5, color: WARNING },
        itemStyle: { color: WARNING },
        // 80/20 法则参考线：累计占比越过 80% 之前的前几类即修复杠杆。
        markLine: {
          silent: true,
          symbol: 'none',
          data: [
            {
              yAxis: 80,
              lineStyle: {
                color: hexA(WARNING, 0.4),
                type: 'dashed',
                width: 1,
              },
              label: {
                formatter: '80%',
                position: 'insideEndTop',
                color: WARNING,
                fontSize: 10,
              },
            },
          ],
        },
      },
    ],
  };
}

export interface HealthGaugeSpec {
  score: number | null;
  label: string;
  color: string;
}

/** 综合健康分环形仪表（Datadog service health 式）。 */
export function healthGaugeOption(spec: HealthGaugeSpec): EChartsOption {
  const { score, label, color } = spec;
  return {
    series: [
      {
        type: 'gauge',
        startAngle: 210,
        endAngle: -30,
        min: 0,
        max: 100,
        radius: '105%',
        center: ['50%', '58%'],
        progress: {
          show: true,
          width: 9,
          roundCap: true,
          itemStyle: { color },
        },
        axisLine: {
          roundCap: true,
          lineStyle: { width: 9, color: [[1, GRID_TEXT]] },
        },
        pointer: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        title: {
          offsetCenter: [0, '58%'],
          fontSize: 10,
          color: MUTED_TEXT,
        },
        detail: {
          offsetCenter: [0, '-6%'],
          fontSize: 26,
          fontWeight: 600,
          formatter: score == null ? '—' : String(score),
          color: '#e6e9ef',
        },
        data: [{ value: score ?? 0, name: label }],
        animation: false,
      },
    ],
  };
}

// ---------------------------------------------------------------------------
// 组合式装饰器（OCP）：为既有 option 追加告警事件标注，不修改任何原 builder。
// ---------------------------------------------------------------------------

export interface AlertMarkSpec {
  /** markPoint 挂载的目标系列名，由调用方声明（装饰器不猜测系列语义）。 */
  targetSeriesName: string;
  /** 目标系列在该桶的纵值取值器。返回 null 的桶不打点。 */
  valueAt: (p: MonitoringPoint) => number | null;
  /** 阈值突破判定：返回 true 的桶视为一次告警事件。 */
  breached: (p: MonitoringPoint) => boolean;
  /** 事件名（i18n 后传入），进入 markPoint.data[i].name。 */
  label: string;
}

/**
 * 把逐桶阈值突破标记为红色事件点叠加在目标系列上 ——
 * 告警从"当前状态"变成时间轴上可归因的"事件"（Grafana annotations 模式）。
 * 纯组合：无命中时原样返回；已有 markPoint 时追加而非覆盖。
 */
export function withAlertMarks(
  option: EChartsOption,
  points: MonitoringPoint[],
  spec: AlertMarkSpec,
): EChartsOption {
  const hits = points.filter(
    (p) => spec.breached(p) && spec.valueAt(p) != null,
  );
  if (hits.length === 0 || !Array.isArray(option.series)) return option;

  const seriesList = option.series as unknown as Array<
    Record<string, unknown> | undefined
  >;
  const target = seriesList.find((s) => s?.name === spec.targetSeriesName);
  if (!target) return option;

  const prev = (target.markPoint ?? {}) as Record<string, unknown>;
  const prevData = Array.isArray(prev.data) ? prev.data : [];
  const marks = hits.map((p) => ({
    name: spec.label,
    coord: [p.ts, spec.valueAt(p)] as [string, number],
    symbol: 'circle',
    symbolSize: 8,
    itemStyle: {
      color: DANGER,
      borderColor: hexA(DANGER, 0.25),
      borderWidth: 4,
    },
    label: { show: false },
  }));
  target.markPoint = {
    ...prev,
    silent: false,
    animation: false,
    data: [...prevData, ...marks],
  };
  return option;
}

export interface ThresholdLineSpec {
  /** 警戒线的 Y 值（与目标系列同量纲）。 */
  yAxis: number;
  /** 线上标签文案（i18n 后传入）。 */
  label: string;
}

/**
 * 为既有 option 的目标系列追加水平阈值警戒线 ——
 * 与 withAlertMarks 同构的纯组合装饰器，不修改任何原 builder。
 * 已有 markLine 时追加而非覆盖；找不到目标系列时原样返回。
 */
export function withThresholdLine(
  option: EChartsOption,
  targetSeriesName: string,
  spec: ThresholdLineSpec,
): EChartsOption {
  if (!Array.isArray(option.series)) return option;

  const seriesList = option.series as unknown as Array<
    Record<string, unknown> | undefined
  >;
  const target = seriesList.find((s) => s?.name === targetSeriesName);
  if (!target) return option;

  const prev = (target.markLine ?? {}) as Record<string, unknown>;
  const prevData = Array.isArray(prev.data) ? prev.data : [];
  target.markLine = {
    ...prev,
    silent: true,
    symbol: 'none',
    data: [
      ...prevData,
      {
        yAxis: spec.yAxis,
        lineStyle: { color: hexA(DANGER, 0.35), type: 'dashed', width: 1 },
        label: {
          formatter: spec.label,
          position: 'insideEndTop',
          color: DANGER,
          fontSize: 10,
        },
      },
    ],
  };
  return option;
}
