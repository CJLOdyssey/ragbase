import type { FeedbackMetrics, RetrievalMetrics } from '../../types/monitoring';

/**
 * 综合健康分 —— 纯计算模块（SRP：计算与展示分离，可独立单测）。
 *
 * 计分模型：每个因子按「当前值 / 阈值」归一，阈值处恰好 70 分——
 * 与告警语义对齐（触发告警 ⇔ 因子跌破 70）：
 * - 低优指标（空召回率、P95 延迟）：x = current / threshold，
 *   x ∈ [0,1] 线性 100→70；x ∈ (1,2] 线性 70→0；x > 2 记 0。
 * - 高优指标（好评率）：y = current / threshold，y ≥ 1 封顶 100；否则 70y。
 *
 * 因子缺数据（null）时按剩余因子权重等比重分配；全部缺失 → 总分 null。
 */

export interface HealthThresholds {
  /** 空召回率告警阈值（百分比，与后端 max_empty_recall_pct 同源）。 */
  maxEmptyRecallPct: number;
  /** P95 延迟 SLO（毫秒，与后端 max_p95_latency_ms 同源）。 */
  maxP95LatencyMs: number;
  /** 好评率下限（与后端 min_good_ratio 同源）。 */
  minGoodRatio: number;
}

export const DEFAULT_HEALTH_THRESHOLDS: HealthThresholds = {
  maxEmptyRecallPct: 15,
  maxP95LatencyMs: 8000,
  minGoodRatio: 0.6,
};

export const HEALTH_WEIGHTS = {
  retrieval: 0.3,
  latency: 0.3,
  satisfaction: 0.4,
} as const;

export type HealthFactorKey = keyof typeof HEALTH_WEIGHTS;

export interface HealthFactor {
  key: HealthFactorKey;
  /** null = 该因子窗口内无样本。 */
  score: number | null;
  /** 重分配后的最终权重。 */
  weight: number;
}

/** 低优指标：阈值处 70 分，2× 阈值处归零。 */
export function factorScoreLower(currentOverThreshold: number): number {
  const x = Math.max(currentOverThreshold, 0);
  if (x <= 1) return 100 - 30 * x;
  return Math.max(0, 70 - 70 * (x - 1));
}

/** 高优指标：阈值处 70 分，达标封顶 100。 */
export function factorScoreHigher(currentOverThreshold: number): number {
  if (!Number.isFinite(currentOverThreshold) || currentOverThreshold <= 0) {
    return 0;
  }
  return Math.min(100, 70 * currentOverThreshold);
}

const clampScore = (v: number) => Math.min(100, Math.max(0, Math.round(v)));

export function computeHealthScore(
  retrieval: Pick<RetrievalMetrics, 'empty_recall_rate' | 'latency_p95_ms' | 'total'>,
  feedback: Pick<FeedbackMetrics, 'good_ratio' | 'total'>,
  thresholds: HealthThresholds = DEFAULT_HEALTH_THRESHOLDS,
): { score: number | null; factors: HealthFactor[] } {
  const rawScores: Record<HealthFactorKey, number | null> = {
    retrieval:
      retrieval.total > 0
        ? clampScore(factorScoreLower((retrieval.empty_recall_rate * 100) / thresholds.maxEmptyRecallPct))
        : null,
    latency:
      retrieval.latency_p95_ms != null
        ? clampScore(factorScoreLower(retrieval.latency_p95_ms / thresholds.maxP95LatencyMs))
        : null,
    satisfaction:
      feedback.good_ratio != null && feedback.total > 0
        ? clampScore(factorScoreHigher(feedback.good_ratio / thresholds.minGoodRatio))
        : null,
  };

  const activeWeight = (Object.keys(rawScores) as HealthFactorKey[])
    .filter((k) => rawScores[k] !== null)
    .reduce((sum, k) => sum + HEALTH_WEIGHTS[k], 0);

  const factors = (Object.keys(rawScores) as HealthFactorKey[]).map((key) => ({
    key,
    score: rawScores[key],
    // 缺数据因子的权重等比例让渡给有效因子，总分不因缺数据而虚低。
    weight: activeWeight > 0 && rawScores[key] !== null
      ? HEALTH_WEIGHTS[key] / activeWeight
      : 0,
  }));

  const weighted = factors.reduce(
    (sum, f) => sum + (f.score ?? 0) * f.weight,
    0,
  );
  return { score: activeWeight > 0 ? clampScore(weighted) : null, factors };
}
