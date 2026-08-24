import type { EChartsOption } from '../../shared/EChart';
import {
  ACCENT,
  DANGER,
  hexA,
  MUTED_TEXT,
  spansAcrossYear,
  WARNING,
} from './shared';

export interface LatencyHeatmapSpec {
  points: Array<{ ts: string; counts: number[] }>;
  binLabels: string[];
  intraday: boolean;
}

/** 延迟分布热力图：x=时间桶 y=延迟区间 色=次数（visualMap 连续色阶）。 */
export function latencyHeatmapOption(spec: LatencyHeatmapSpec): EChartsOption {
  const { points, binLabels, intraday } = spec;
  const includeYear =
    points.length > 1 &&
    spansAcrossYear(
      +new Date(points[0].ts),
      +new Date(points[points.length - 1].ts),
    );

  const tsLabels = points.map((pt) => {
    const d = new Date(pt.ts);
    const pad = (n: number) => String(n).padStart(2, '0');
    return includeYear
      ? `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
      : intraday
        ? `${pad(d.getHours())}:${pad(d.getMinutes())}`
        : `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  });

  const data: Array<[number, number, number]> = [];
  let maxVal = 0;
  for (let x = 0; x < points.length; x++) {
    for (let y = 0; y < points[x].counts.length; y++) {
      const c = points[x].counts[y];
      if (c > 0) data.push([x, y, c]);
      if (c > maxVal) maxVal = c;
    }
  }

  return {
    grid: { left: 64, right: 18, top: 30, bottom: 40 },
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(17,21,28,0.96)',
      borderColor: 'rgba(255,255,255,0.08)',
      borderWidth: 1,
      padding: [6, 10],
      textStyle: { color: '#e6e9ef', fontSize: 11 },
      formatter: (params: unknown) => {
        const p = params as { value: [number, number, number] };
        const [x, y, count] = p.value;
        return `<div style="font-weight:600">${tsLabels[x]}</div><div style="margin-top:4px">${binLabels[y]}：<b>${count} 次</b></div>`;
      },
    },
    xAxis: {
      type: 'category',
      data: tsLabels,
      splitArea: { show: true },
      axisLabel: { color: MUTED_TEXT, fontSize: 10, hideOverlap: true },
    },
    yAxis: {
      type: 'category',
      data: binLabels,
      inverse: true,
      splitArea: { show: true },
      axisLabel: { color: MUTED_TEXT, fontSize: 10 },
    },
    visualMap: {
      min: 0,
      max: maxVal || 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      itemWidth: 10,
      itemHeight: 80,
      textStyle: { color: MUTED_TEXT, fontSize: 10 },
      inRange: {
        color: [
          hexA(ACCENT, 0.08),
          hexA(ACCENT, 0.25),
          hexA(ACCENT, 0.45),
          ACCENT,
          WARNING,
          DANGER,
        ],
      },
    },
    series: [
      {
        type: 'heatmap',
        data,
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' },
        },
      },
    ],
  };
}
