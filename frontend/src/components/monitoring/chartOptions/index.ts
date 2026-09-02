// 按需导出所有 chartOptions builder — 与旧 chartOptions.ts 的公共 API 完全一致。
export { hexA, compact, legendStyle } from './shared';
export type { SeriesFmtMap } from './shared';
export {
  spansAcrossYear,
  spansYear,
  timeAxis,
  tooltipTime,
  alignedGhost,
  ghostSeries,
} from './shared';
export {
  ACCENT,
  SUCCESS,
  WARNING,
  DANGER,
  MUTED_TEXT,
  GRID_TEXT,
  GHOST_STYLE,
} from './shared';
export { axisTooltip } from './shared';

export {
  periodDelta,
  ratioDelta,
  weightedDelta,
  volumeTrendOption,
  lineTrendOption,
  latencyTrendOption,
} from './trend';
export type {
  KpiDelta,
  VolumeTrendSpec,
  LineTrendSpec,
  LatencyTrendSpec,
} from './trend';

export { retrievalFunnelOption } from './funnel';
export type { FunnelStage } from './funnel';

export { rootCauseParetoOption } from './pareto';
export type { RootCauseParetoSpec } from './pareto';

export { healthGaugeOption, healthTrendOption } from './health';
export type { HealthGaugeSpec, HealthTrendSpec } from './health';

export {
  withBreachRegions,
  withBreachTint,
  withThresholdLine,
} from './decorators';
export type {
  BreachRegionSpec,
  BreachTintSpec,
  ThresholdLineSpec,
} from './decorators';

export { feedbackCompositionOption } from './composition';
export type { FeedbackCompositionSpec } from './composition';

export { latencyHeatmapOption } from './heatmapChart';
export type { LatencyHeatmapSpec } from './heatmapChart';

export { latencyScatterOption } from './scatter';
export type { LatencyScatterSpec } from './scatter';
