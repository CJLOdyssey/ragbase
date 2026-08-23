import { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import {
  BarChart,
  FunnelChart,
  GaugeChart,
  LineChart,
  type BarSeriesOption,
  type FunnelSeriesOption,
  type GaugeSeriesOption,
  type LineSeriesOption,
} from 'echarts/charts';
import {
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  MarkPointComponent,
  TooltipComponent,
  type GridComponentOption,
  type LegendComponentOption,
  type MarkLineComponentOption,
  type MarkPointComponentOption,
  type TooltipComponentOption,
} from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';
import type { ComposeOption } from 'echarts/core';

export type EChartsOption = ComposeOption<
  | BarSeriesOption
  | FunnelSeriesOption
  | GaugeSeriesOption
  | LineSeriesOption
  | GridComponentOption
  | LegendComponentOption
  | MarkLineComponentOption
  | MarkPointComponentOption
  | TooltipComponentOption
>;

// 按需注册：折线/柱/漏斗/仪表族 + 网格/图例/标线标点/提示框 + SVG 渲染器。
echarts.use([
  BarChart,
  FunnelChart,
  GaugeChart,
  LineChart,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  MarkPointComponent,
  TooltipComponent,
  SVGRenderer,
]);

interface Props {
  option: EChartsOption;
  height?: number;
  className?: string;
  ariaLabel?: string;
  testId?: string;
}

/**
 * Apache ECharts 薄封装 —— 仅承担生命周期（init/setOption/dispose/resize），
 * 图表语义完全由调用方通过 option 表达。
 */
export default function EChart({
  option,
  height = 180,
  className,
  ariaLabel,
  testId,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const chart = echarts.init(el, undefined, { renderer: 'svg' });
    chartRef.current = chart;
    // jsdom 无 ResizeObserver：测试环境退化为静态尺寸。
    const observer =
      typeof ResizeObserver === 'undefined'
        ? null
        : new ResizeObserver(() => chart.resize());
    observer?.observe(el);
    return () => {
      observer?.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    // notMerge：窗口切换时旧系列不残留。
    chartRef.current?.setOption(option, true);
  }, [option]);

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height, userSelect: 'none' }}
      className={className}
      role="img"
      aria-label={ariaLabel}
      data-testid={testId}
    />
  );
}
