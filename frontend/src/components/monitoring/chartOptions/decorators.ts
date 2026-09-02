import type { MonitoringPoint } from '../../../types/monitoring';
import type { EChartsOption } from '../../shared/EChart';
import { DANGER, hexA } from './shared';

/**
 * ECharts option.series 的运行时契约：官方 TS 类型不暴露 name/data/markArea/markLine，
 * 这里定义最小必要子集，消除 4 处 `as unknown as` 逃生舱（总纲 ISP + 高内聚）。
 */
interface EChartsSeries {
  name?: string;
  data?: unknown[];
  markArea?: Record<string, unknown>;
  markLine?: Record<string, unknown>;
  [key: string]: unknown;
}

/** 安全提取 series 列表（非数组时返回空）。 */
function getSeriesList(option: EChartsOption): EChartsSeries[] {
  return Array.isArray(option.series) ? (option.series as EChartsSeries[]) : [];
}

// ── 阈值越线的本体编码（Grafana thresholdsStyle "series"/area 模式）────────

export interface BreachTintSpec {
  targetSeriesName: string;
  valueAt: (p: MonitoringPoint) => number | null;
  breached: (p: MonitoringPoint) => boolean;
  /** 越线数据项的本体颜色（柱图整柱着色）。 */
  color: string;
}

/**
 * 把逐桶阈值突破编码进系列本体：越线数据项改写为 { value, itemStyle }，
 * 颜色长在数据几何上，不新增悬浮元素（替代旧 markPoint 红点）。
 * 纯组合：无命中时原样返回。
 */
export function withBreachTint(
  option: EChartsOption,
  points: MonitoringPoint[],
  spec: BreachTintSpec,
): EChartsOption {
  const seriesList = getSeriesList(option);
  const target = seriesList.find((s) => s.name === spec.targetSeriesName);
  if (!target || !Array.isArray(target.data)) return option;

  const breachedTs = new Set(
    points
      .filter((p) => spec.breached(p) && spec.valueAt(p) != null)
      .map((p) => p.ts),
  );
  if (breachedTs.size === 0) return option;

  target.data = target.data.map((item) => {
    const ts = Array.isArray(item) ? item[0] : null;
    if (typeof ts !== 'string' || !breachedTs.has(ts)) return item;
    return { value: item, itemStyle: { color: spec.color } };
  });
  return option;
}

export interface BreachRegionSpec {
  breached: (p: MonitoringPoint) => boolean;
}

/**
 * 连续越线时段归并为半透明底纹（markArea，Grafana alert regions 模式）——
 * 用于面积/堆叠图等颜色无法直接落在几何体上的场景。
 * 纯组合：无越线时原样返回；已有 markArea 时追加而非覆盖。
 */
export function withBreachRegions(
  option: EChartsOption,
  targetSeriesName: string,
  points: MonitoringPoint[],
  spec: BreachRegionSpec,
): EChartsOption {
  const runs: Array<[string, string]> = [];
  let start: string | null = null;
  let last: string | null = null;
  for (const p of points) {
    if (spec.breached(p)) {
      if (start === null) start = p.ts;
      last = p.ts;
    } else if (start !== null && last !== null) {
      runs.push([start, last]);
      start = null;
    }
  }
  if (start !== null && last !== null) runs.push([start, last]);
  if (runs.length === 0) return option;

  const seriesList = getSeriesList(option);
  const target = seriesList.find((s) => s.name === targetSeriesName);
  if (!target) return option;

  const prev = target.markArea ?? {};
  const prevData = Array.isArray(prev.data) ? prev.data : [];
  target.markArea = {
    ...prev,
    silent: true,
    animation: false,
    itemStyle: { color: hexA(DANGER, 0.08) },
    data: [...prevData, ...runs.map(([a, b]) => [{ xAxis: a }, { xAxis: b }])],
  };
  return option;
}

// ── 阈值警戒线（与上面同构的纯组合装饰器）──────────────────────

export interface ThresholdLineSpec {
  yAxis: number;
  label: string;
}

/**
 * 为既有 option 的目标系列追加水平阈值警戒线 ——
 * 已有 markLine 时追加而非覆盖；找不到目标系列时原样返回。
 */
export function withThresholdLine(
  option: EChartsOption,
  targetSeriesName: string,
  spec: ThresholdLineSpec,
): EChartsOption {
  const seriesList = getSeriesList(option);
  const target = seriesList.find((s) => s.name === targetSeriesName);
  if (!target) return option;

  const prev = target.markLine ?? {};
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
