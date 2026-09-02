import api from './instance';

export interface RetrievalLogItem {
  id: string;
  query: string;
  sessionId: string | null;
  latencyMs: number;
  hitCount: number;
  topK: number;
  rerank: boolean;
  minScore: number | null;
  sources: Array<{
    asset_id: string;
    asset_name: string;
    similarity: number;
  }> | null;
  createdAt: string;
}

export interface RetrievalLogListResponse {
  items: RetrievalLogItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface RetrievalLogParams {
  page?: number;
  page_size?: number;
  empty_only?: boolean;
  max_latency_ms?: number;
  since_hours?: number;
  /** ISO 8601 — custom absolute range wins over since_hours. */
  since?: string;
  until?: string;
}

export async function listRetrievalLogs(
  params?: RetrievalLogParams,
): Promise<RetrievalLogListResponse> {
  const { data } = await api.get('/retrieval-logs', { params });
  return data;
}

export interface LatencyBucket {
  range: string;
  count: number;
  percentage: number;
}

export interface HitRateStats {
  total: number;
  emptyRecall: number;
  hitRecall: number;
  emptyRecallRate: number;
}

export interface VolumeTrendPoint {
  /** ISO 8601 bucket start (UTC). */
  ts: string;
  count: number;
  avgLatency: number;
}

export interface DailyActivity {
  day: number;
  hour: number;
  count: number;
}

export interface RetrievalStatsResponse {
  latencyDistribution: LatencyBucket[];
  hitRate: HitRateStats;
  volumeTrend: VolumeTrendPoint[];
  dailyActivity: DailyActivity[];
}

export interface RetrievalStatsParams {
  empty_only?: boolean;
  max_latency_ms?: number;
  since_hours?: number;
  /** ISO 8601 — custom absolute range wins over since_hours. */
  since?: string;
  until?: string;
}

export async function getRetrievalStats(
  params?: RetrievalStatsParams,
): Promise<RetrievalStatsResponse> {
  const { data } = await api.get('/retrieval-logs/stats', { params });
  return data;
}
