import { useQuery } from '@tanstack/react-query';
import type { TimeRangeQuery } from '../../types/monitoring';
import {
  fetchHealthScoreHistory,
  fetchLatencyHeatmap,
  fetchLatencyScatter,
  fetchMonitoringSummary,
  fetchMonitoringTimeseries,
} from '../../api/client/monitoring';

/** 主图时间刻度粒度：24h 内按小时，更长窗口按天；自定义范围按跨度判断。 */
export function isIntradayQuery(query: TimeRangeQuery): boolean {
  if (query.since && query.until) {
    const spanMs =
      new Date(query.until).getTime() - new Date(query.since).getTime();
    return spanMs <= 24 * 60 * 60 * 1000;
  }
  return query.window_hours > 0 && query.window_hours <= 24;
}

export function useMonitoringSummaryQuery(timeQuery: TimeRangeQuery) {
  return useQuery({
    queryKey: ['monitoring', timeQuery],
    queryFn: () => fetchMonitoringSummary(timeQuery),
  });
}

/** 健康分历史快照（小时级 beat 采样），驱动卡片内的趋势 sparkline。 */
export function useHealthScoreHistoryQuery(hours = 168) {
  return useQuery({
    queryKey: ['monitoring-health-history', hours],
    queryFn: () => fetchHealthScoreHistory(hours),
    // 快照每小时才写一条，无需频繁轮询。
    refetchInterval: 5 * 60 * 1000,
  });
}

export function useMonitoringTimeseriesQuery(timeQuery: TimeRangeQuery) {
  // 预设窗口才请求上期序列（真·环比基线 + ghost 虚线）；自定义范围与全量无上期。
  const includePrevious = timeQuery.window_hours > 0 && !timeQuery.since;
  return useQuery({
    queryKey: ['monitoring-timeseries', timeQuery],
    queryFn: () => fetchMonitoringTimeseries(timeQuery, includePrevious),
  });
}

export function useLatencyHeatmapQuery(timeQuery: TimeRangeQuery) {
  return useQuery({
    queryKey: ['monitoring-latency-heatmap', timeQuery],
    queryFn: () => fetchLatencyHeatmap(timeQuery),
  });
}

export function useLatencyScatterQuery(timeQuery: TimeRangeQuery) {
  return useQuery({
    queryKey: ['monitoring-latency-scatter', timeQuery],
    queryFn: () => fetchLatencyScatter({ ...timeQuery, limit: 1000 }),
  });
}
