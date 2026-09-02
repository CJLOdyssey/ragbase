export interface RetrievalMetrics {
  total: number;
  empty_recall_count: number;
  empty_recall_rate: number;
  /** 超延迟 SLO 请求数与占比 —— 错误预算健康分的延迟维度数据源。 */
  slow_count: number;
  slow_rate: number;
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

export type HealthFactorKey = 'retrieval' | 'latency' | 'satisfaction';

/** 服务端错误预算模型算出的单因子：分数即预算剩余百分比。 */
export interface HealthFactorPayload {
  key: HealthFactorKey;
  /** null = 该因子窗口内无样本。 */
  score: number | null;
  /** 重分配后的最终权重。 */
  weight: number;
}

/** 综合健康分（服务端计算，Google SRE 错误预算模型）。 */
export interface HealthScorePayload {
  score: number | null;
  factors: HealthFactorPayload[];
}

export interface MonitoringSummary {
  window_hours: number;
  retrieval: RetrievalMetrics;
  feedback: FeedbackMetrics;
  health_score: HealthScorePayload;
  alerts: QualityAlert[];
}

export interface HealthScoreHistoryPoint {
  ts: string;
  score: number | null;
}

export interface HealthScoreHistoryResponse {
  hours: number;
  points: HealthScoreHistoryPoint[];
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
  'retrieval_miss' | 'wrong_answer' | 'bad_format' | 'other';

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

export interface LatencyHeatmapPoint {
  ts: string;
  counts: number[];
}

export interface LatencyHeatmapResponse {
  window_hours: number;
  bucket_hours: number;
  bin_edges_ms: number[];
  points: LatencyHeatmapPoint[];
}

export interface LatencyScatterItem {
  ts: string;
  hits: number;
  latency_ms: number;
}

export interface LatencyScatterResponse {
  window_hours: number;
  total: number;
  sampled: number;
  items: LatencyScatterItem[];
}
