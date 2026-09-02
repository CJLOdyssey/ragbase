import type { EChartsOption } from '../../shared/EChart';
import { ACCENT, compact, hexA, MUTED_TEXT } from './shared';

export interface RootCauseParetoSpec {
  categories: string[];
  counts: number[];
  cumulativePct: number[];
  labels: { count: string; cumulative: string };
}

/** 57.1 → "57.1%"；100 → "100%"。 */
const fmtPct = (v: number): string =>
  `${Number.isInteger(v) ? v : v.toFixed(1)}%`;

interface ParetoDatum {
  name: string;
  value: number;
  dataIndex: number;
}

/**
 * 差评根因排序条（Pareto 的现代面板形态）：降序横向条形，
 * 条尾标签携带「次数 · 累计%」——80/20 决策信息由数字承担。
 * 不绘制累计折线/顶部 % 轴：类目少时折线被误读为时间趋势；
 * 自带 item tooltip，不复用时间轴版 axisTooltip（其假定元组值，标量下产生 NaN）。
 */
export function rootCauseParetoOption(
  spec: RootCauseParetoSpec,
): EChartsOption {
  const { categories, counts, cumulativePct, labels } = spec;
  return {
    grid: { left: 84, right: 96, top: 16, bottom: 28 },
    tooltip: {
      trigger: 'item',
      confine: true,
      backgroundColor: 'rgba(17,21,28,0.96)',
      borderColor: 'rgba(255,255,255,0.08)',
      borderWidth: 1,
      padding: [8, 12],
      textStyle: { color: '#e6e9ef', fontSize: 12 },
      formatter: (params: unknown) => {
        const p = params as ParetoDatum;
        return (
          `<div style="font-weight:600">${p.name}</div>` +
          `<div style="margin-top:4px">${labels.count}：<b>${compact(p.value)}</b></div>` +
          `<div style="margin-top:4px">${labels.cumulative}：<b>${fmtPct(cumulativePct[p.dataIndex] ?? 0)}</b></div>`
        );
      },
    },
    xAxis: {
      type: 'value',
      splitNumber: 2,
      splitLine: { show: false },
      axisLabel: { show: false },
    },
    yAxis: {
      type: 'category',
      data: categories,
      inverse: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: MUTED_TEXT, fontSize: 11 },
    },
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
          formatter: (params: unknown) => {
            const p = params as ParetoDatum;
            return `${compact(p.value)} · ${fmtPct(cumulativePct[p.dataIndex] ?? 0)}`;
          },
        },
      },
    ],
  };
}
