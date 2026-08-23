export interface RetrievalMetrics {
  total: number;
  empty_recall_count: number;
  empty_recall_rate: number;
  avg_hit_count: number | null;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  latency_p99_ms: number | null;
}

export interface FeedbackMetrics {
  total: number;
  good_count: number;
  bad_count: number;
  good_ratio: number | null;
  /** 窗口内成功完成的回答数 —— 好评率的覆盖分母。 */
  answered_runs: number;
}

export interface QualityAlert {
  level: 'warning' | 'critical';
  code: string;
  current: number;
  threshold: number;
}

export interface MonitoringSummary {
  window_hours: number;
  retrieval: RetrievalMetrics;
  feedback: FeedbackMetrics;
  alerts: QualityAlert[];
}

export interface MonitoringPoint {
  /** ISO timestamp of the bucket start (aligned grid, oldest → newest). */
  ts: string;
  retrievals: number;
  empty_count: number;
  avg_hits: number | null;
  avg_latency_ms: number | null;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  latency_p99_ms: number | null;
  good: number;
  bad: number;
}

export interface MonitoringTimeseries {
  window_hours: number;
  bucket_hours: number;
  points: MonitoringPoint[];
  /** 对齐的上期序列（include_previous=true 时返回），index 与 points 一一对应。 */
  previous_points: MonitoringPoint[] | null;
}

/** 监控页统一时间范围：预设窗口或自定义 since/until（ISO 字符串）。 */
export interface TimeRangeQuery {
  window_hours: number;
  since?: string;
  until?: string;
}

export type ReviewStatus = 'pending' | 'resolved' | 'dismissed';
export type ReviewRootCause =
  | 'retrieval_miss'
  | 'wrong_answer'
  | 'bad_format'
  | 'other';

export interface BadFeedbackReview {
  status: ReviewStatus;
  root_cause: ReviewRootCause | null;
  note: string | null;
  updated_at: string | null;
}

export interface BadFeedbackItem {
  feedback_id: string;
  run_id: string;
  query: string | null;
  answer: string | null;
  created_at: string | null;
  review: BadFeedbackReview | null;
}

export interface BadFeedbackResponse {
  items: BadFeedbackItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface RootCauseEntry {
  cause: ReviewRootCause;
  count: number;
}

export interface RootCauseBreakdown {
  window_hours: number;
  total_bad: number;
  /** 未审查（无 review 记录或 status=pending）。 */
  pending: number;
  resolved: number;
  dismissed: number;
  causes: RootCauseEntry[];
}

export type TopQueryKind = 'empty' | 'slow';

export interface TopQueryItem {
  query: string;
  count: number;
  avg_latency_ms: number | null;
}

export interface TopQueriesResponse {
  window_hours: number;
  kind: TopQueryKind;
  items: TopQueryItem[];
}
