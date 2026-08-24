import type { HealthScoreHistoryPoint } from '../../../types/monitoring';
import type { EChartsOption } from '../../shared/EChart';
import { axisTooltip, GRID_TEXT, hexA, MUTED_TEXT } from './shared';

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

export interface HealthTrendSpec {
  /** 升序快照序列；score=null 的点断线不连。 */
  points: HealthScoreHistoryPoint[];
  color?: string;
}

/** 健康分历史 sparkline（卡片内嵌，小时级 beat 快照）。 */
export function healthTrendOption(spec: HealthTrendSpec): EChartsOption {
  const { points, color = '#34d399' } = spec;
  const data = points.map((p) => [p.ts, p.score] as [string, number | null]);
  return {
    grid: { left: 2, right: 2, top: 4, bottom: 2, containLabel: false },
    tooltip: axisTooltip(
      new Map([['分数', (v) => String(Math.round(v))]]),
      true,
    ),
    xAxis: {
      type: 'time',
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { show: false },
      splitLine: { show: false },
    },
    series: [
      {
        name: '分数',
        type: 'line',
        data,
        smooth: 0.3,
        showSymbol: false,
        connectNulls: false,
        lineStyle: { width: 1.5, color },
        itemStyle: { color },
        areaStyle: { color: hexA(color, 0.12) },
      },
    ],
  };
}
