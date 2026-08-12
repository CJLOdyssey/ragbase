export interface RetrievalMetrics {
  total: number;
  empty_recall_count: number;
  empty_recall_rate: number;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
}

export interface FeedbackMetrics {
  total: number;
  good_count: number;
  bad_count: number;
  good_ratio: number | null;
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
