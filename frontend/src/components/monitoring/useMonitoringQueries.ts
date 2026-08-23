import { useQuery } from '@tanstack/react-query';
import {
  fetchMonitoringSummary,
  fetchMonitoringTimeseries,
} from '../../api/client/monitoring';
import type { TimeRangeQuery } from '../../types/monitoring';

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

export function useMonitoringTimeseriesQuery(timeQuery: TimeRangeQuery) {
  // 预设窗口才请求上期序列（真·环比基线 + ghost 虚线）；自定义范围与全量无上期。
  const includePrevious = timeQuery.window_hours > 0 && !timeQuery.since;
  return useQuery({
    queryKey: ['monitoring-timeseries', timeQuery],
    queryFn: () => fetchMonitoringTimeseries(timeQuery, includePrevious),
  });
}
