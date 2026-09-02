import type { EChartsOption } from '../../shared/EChart';
import { ACCENT, hexA } from './shared';

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
