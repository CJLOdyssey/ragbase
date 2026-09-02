import type { MonitoringPoint } from '../../../types/monitoring';
import type { EChartsOption } from '../../shared/EChart';
import {
  axisTooltip,
  DANGER,
  GRID_TEXT,
  hexA,
  legendStyle,
  MUTED_TEXT,
  spansYear,
  SUCCESS,
  timeAxis,
  type SeriesFmtMap,
} from './shared';

export interface FeedbackCompositionSpec {
  points: MonitoringPoint[];
  labels: { good: string; bad: string; unrated: string };
  intraday: boolean;
}

/** 反馈构成趋势：逐桶 百分比堆叠柱 —— 好评/差评/未评价的构成随时间迁移。 */
export function feedbackCompositionOption(
  spec: FeedbackCompositionSpec,
): EChartsOption {
  const { points, labels, intraday } = spec;
  const includeYear = spansYear(points);

  const goodData: Array<[string, number]> = [];
  const badData: Array<[string, number]> = [];
  const unratedData: Array<[string, number]> = [];

  for (const p of points) {
    const rated = p.good + p.bad;
    const unrated = Math.max(p.retrievals - rated, 0);
    const denom = Math.max(p.retrievals, 0);
    const pct =
      denom > 0 ? (v: number) => Math.round((v / denom) * 1000) / 10 : () => 0;
    goodData.push([p.ts, pct(p.good)]);
    badData.push([p.ts, pct(p.bad)]);
    unratedData.push([p.ts, pct(unrated)]);
  }

  const fmts: SeriesFmtMap = new Map([
    [labels.good, (v) => `${v.toFixed(1)}%`],
    [labels.bad, (v) => `${v.toFixed(1)}%`],
    [labels.unrated, (v) => `${v.toFixed(1)}%`],
  ]);

  return {
    grid: { left: 44, right: 18, top: 30, bottom: 26 },
    legend: legendStyle,
    tooltip: axisTooltip(fmts, includeYear),
    xAxis: timeAxis(intraday, includeYear),
    yAxis: {
      type: 'value',
      max: 100,
      splitNumber: 3,
      splitLine: { lineStyle: { color: GRID_TEXT, type: 'dashed' } },
      axisLabel: { color: MUTED_TEXT, fontSize: 10, formatter: '{value}%' },
    },
    series: [
      {
        name: labels.good,
        type: 'bar',
        stack: 'feedback',
        data: goodData,
        barMaxWidth: 14,
        itemStyle: { color: hexA(SUCCESS, 0.75) },
      },
      {
        name: labels.bad,
        type: 'bar',
        stack: 'feedback',
        data: badData,
        barMaxWidth: 14,
        itemStyle: { color: hexA(DANGER, 0.75) },
      },
      {
        name: labels.unrated,
        type: 'bar',
        stack: 'feedback',
        data: unratedData,
        barMaxWidth: 14,
        itemStyle: { color: hexA(MUTED_TEXT, 0.35) },
      },
    ],
  };
}
