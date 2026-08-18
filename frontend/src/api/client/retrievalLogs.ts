import api from './instance';

export interface RetrievalLogItem {
  id: string;
  query: string;
  session_id: string | null;
  latency_ms: number;
  hit_count: number;
  top_k: number;
  rerank: boolean;
  min_score: number | null;
  sources: Array<{ asset_id: string; asset_name: string; similarity: number }> | null;
  created_at: string;
}

export interface RetrievalLogListResponse {
  items: RetrievalLogItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface RetrievalLogParams {
  page?: number;
  page_size?: number;
  empty_only?: boolean;
  max_latency_ms?: number;
}

export async function listRetrievalLogs(params?: RetrievalLogParams): Promise<RetrievalLogListResponse> {
  const { data } = await api.get('/retrieval-logs', { params });
  return data;
}
