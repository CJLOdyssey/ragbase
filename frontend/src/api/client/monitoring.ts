import type {
  BadFeedbackResponse,
  HealthScoreHistoryResponse,
  LatencyHeatmapResponse,
  LatencyScatterResponse,
  MonitoringSummary,
  MonitoringTimeseries,
  ReviewRootCause,
  ReviewStatus,
  RootCauseBreakdown,
  TimeRangeQuery,
  TopQueriesResponse,
  TopQueryKind,
} from '../../types/monitoring';
import api from './instance';

export async function fetchMonitoringSummary(
  range: TimeRangeQuery,
): Promise<MonitoringSummary> {
  const { data } = await api.get('/monitoring/summary', { params: range });
  return data;
}

export async function fetchHealthScoreHistory(
  hours: number,
): Promise<HealthScoreHistoryResponse> {
  const { data } = await api.get('/monitoring/health-score/history', {
    params: { hours },
  });
  return data;
}

export async function fetchMonitoringTimeseries(
  range: TimeRangeQuery,
  includePrevious = false,
): Promise<MonitoringTimeseries> {
  const { data } = await api.get('/monitoring/timeseries', {
    params: { ...range, include_previous: includePrevious || undefined },
  });
  return data;
}

export async function fetchRootCauses(
  range: TimeRangeQuery,
): Promise<RootCauseBreakdown> {
  const { data } = await api.get('/monitoring/root-causes', { params: range });
  return data;
}

export async function fetchTopQueries(range: {
  window_hours: number;
  since?: string;
  until?: string;
  kind: TopQueryKind;
  limit?: number;
}): Promise<TopQueriesResponse> {
  const { data } = await api.get('/monitoring/top-queries', { params: range });
  return data;
}

export async function fetchBadFeedback(
  params: TimeRangeQuery & {
    status?: ReviewStatus;
    page?: number;
    page_size?: number;
  },
): Promise<BadFeedbackResponse> {
  const { data } = await api.get('/monitoring/bad-feedback', { params });
  return data;
}

export async function reviewBadFeedback(
  feedbackId: string,
  body: {
    status: ReviewStatus;
    root_cause?: ReviewRootCause;
    note?: string;
  },
): Promise<unknown> {
  const { data } = await api.post(
    `/monitoring/bad-feedback/${feedbackId}/review`,
    body,
  );
  return data;
}

export async function fetchLatencyHeatmap(
  range: TimeRangeQuery,
): Promise<LatencyHeatmapResponse> {
  const { data } = await api.get('/monitoring/latency-heatmap', {
    params: range,
  });
  return data;
}

export async function fetchLatencyScatter(
  range: TimeRangeQuery & { limit?: number },
): Promise<LatencyScatterResponse> {
  const { data } = await api.get('/monitoring/latency-scatter', {
    params: range,
  });
  return data;
}
