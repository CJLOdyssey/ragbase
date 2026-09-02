// 检索记录页图表共享轴样式：色值与 monitoring/chartOptions/shared.ts 同源（MUTED 文本），深浅主题均可读。
export const AXIS_TEXT_COLOR = '#8a8f98';
export const AXIS_LINE_COLOR = 'rgba(138,143,152,0.35)';

export const axisLabelBase = {
  color: AXIS_TEXT_COLOR,
  fontSize: 10,
} as const;

export const axisLineBase = {
  axisLine: { lineStyle: { color: AXIS_LINE_COLOR } },
  axisTick: { lineStyle: { color: AXIS_LINE_COLOR } },
} as const;

/** y 轴单位标题（nameLocation 默认 end，置于轴顶左上）。 */
export function axisUnitName(unit: string) {
  return {
    name: unit,
    nameTextStyle: { color: AXIS_TEXT_COLOR, fontSize: 10 },
    nameGap: 10,
  };
}

/** 深浅主题均安全的蓝色热力色阶（透明度渐变，低值不刺眼）。 */
export const HEAT_RAMP = [
  'rgba(59,130,246,0.08)',
  'rgba(59,130,246,0.25)',
  'rgba(59,130,246,0.45)',
  'rgba(59,130,246,0.7)',
  '#3b82f6',
  '#93c5fd',
];
