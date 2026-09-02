import type { EChartsOption } from '../../shared/EChart';
import i18n from '../../../i18n';
import {
  ACCENT,
  compact,
  DANGER,
  hexA,
  legendStyle,
  MUTED_TEXT,
} from './shared';

export interface LatencyScatterSpec {
  items: Array<{ ts: string; hits: number; latencyMs: number }>;
  sloMs: number;
  labels: {
    normal: string;
    slow: string;
    sloLine: string;
    hits: string;
    latency: string;
  };
}

/** 延迟-命中散点图：x=命中数 y=延迟ms，红线=SLO 阈值，红点=超限请求。 */
export function latencyScatterOption(spec: LatencyScatterSpec): EChartsOption {
  const { items, sloMs, labels } = spec;
  const normalData: Array<[number, number]> = [];
  const slowData: Array<[number, number]> = [];

  for (const item of items) {
    const point: [number, number] = [item.hits, item.latencyMs];
    if (item.latencyMs > sloMs) {
      slowData.push(point);
    } else {
      normalData.push(point);
    }
  }

  return {
    grid: { left: 56, right: 18, top: 30, bottom: 28 },
    legend: legendStyle,
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(17,21,28,0.96)',
      borderColor: 'rgba(255,255,255,0.08)',
      borderWidth: 1,
      padding: [6, 10],
      textStyle: { color: '#e6e9ef', fontSize: 11 },
      formatter: (params: unknown) => {
        const p = params as { seriesName: string; value: [number, number] };
        const [hits, latency] = p.value;
        return `<div style="font-weight:600">${p.seriesName}</div><div style="margin-top:4px">${i18n.t('monitoring.scatter.hits')}：<b>${hits}</b></div><div>${i18n.t('monitoring.scatter.latency')}：<b>${Math.round(latency)}ms</b></div>`;
      },
    },
    xAxis: {
      type: 'value',
      name: labels.hits,
      nameTextStyle: { color: MUTED_TEXT, fontSize: 10 },
      minInterval: 1,
      splitLine: { lineStyle: { color: MUTED_TEXT, type: 'dashed' } },
      axisLabel: { color: MUTED_TEXT, fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      name: labels.latency,
      nameTextStyle: { color: MUTED_TEXT, fontSize: 10 },
      scale: true,
      splitLine: { lineStyle: { color: MUTED_TEXT, type: 'dashed' } },
      axisLabel: { color: MUTED_TEXT, fontSize: 10, formatter: compact },
    },
    series: [
      {
        name: labels.normal,
        type: 'scatter',
        data: normalData,
        symbolSize: 7,
        itemStyle: { color: hexA(ACCENT, 0.55) },
        markLine: {
          silent: true,
          symbol: 'none',
          data: [
            {
              yAxis: sloMs,
              lineStyle: {
                color: hexA(DANGER, 0.35),
                type: 'dashed',
                width: 1,
              },
              label: {
                formatter: `${labels.sloLine} ${compact(sloMs)}ms`,
                position: 'insideEndTop',
                color: DANGER,
                fontSize: 10,
              },
            },
          ],
        },
      },
      {
        name: labels.slow,
        type: 'scatter',
        data: slowData,
        symbolSize: 9,
        itemStyle: { color: DANGER },
      },
    ],
  };
}
