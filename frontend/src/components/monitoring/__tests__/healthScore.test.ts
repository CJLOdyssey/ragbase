import {
  computeHealthScore,
  DEFAULT_HEALTH_THRESHOLDS,
  factorScoreHigher,
  factorScoreLower,
} from '../healthScore';

describe('factor scoring curves', { tags: ['unit'] }, () => {
  it('低优指标：阈值处恰好 70 分，2× 阈值归零', () => {
    expect(factorScoreLower(0)).toBe(100);
    expect(factorScoreLower(0.5)).toBe(85);
    expect(factorScoreLower(1)).toBe(70);
    expect(factorScoreLower(1.5)).toBe(35);
    expect(factorScoreLower(2)).toBe(0);
    expect(factorScoreLower(3)).toBe(0); // 不为负
  });

  it('高优指标：阈值处恰好 70 分，达标封顶 100', () => {
    expect(factorScoreHigher(0)).toBe(0);
    expect(factorScoreHigher(0.5)).toBe(35);
    expect(factorScoreHigher(1)).toBe(70);
    expect(factorScoreHigher(1.5)).toBe(100);
    expect(factorScoreHigher(10)).toBe(100);
  });
});

describe('computeHealthScore', { tags: ['unit'] }, () => {
  const retrieval = (emptyRate: number, p95: number | null, total = 100) => ({
    total,
    empty_recall_rate: emptyRate,
    latency_p95_ms: p95,
  });
  const feedback = (ratio: number | null, total = 20) => ({
    good_ratio: ratio,
    total,
  });

  it('全维度达标 → 高分', () => {
    const { score } = computeHealthScore(
      retrieval(0.0333, 2100),
      feedback(0.9),
      DEFAULT_HEALTH_THRESHOLDS,
    );
    expect(score).not.toBeNull();
    expect(score!).toBeGreaterThanOrEqual(90);
  });

  it('空召回爆表（>2× 阈值）→ 检索因子归零拉低总分', () => {
    const { score, factors } = computeHealthScore(
      retrieval(0.5, 2000),
      feedback(0.9),
      DEFAULT_HEALTH_THRESHOLDS,
    );
    const retrievalFactor = factors.find((f) => f.key === 'retrieval')!;
    expect(retrievalFactor.score).toBe(0);
    expect(score!).toBeLessThan(70);
  });

  it('全维度无样本 → 总分为 null 且权重归零', () => {
    // 仅满意度有样本：好评率 0.9 / 阈值 0.6 = 1.5 → 因子满分，总分即满分。
    const { score, factors } = computeHealthScore(
      retrieval(0, null, 0),
      feedback(null, 0),
      DEFAULT_HEALTH_THRESHOLDS,
    );
    // 检索因子 total=0 无样本、延迟无样本、满意度无反馈 → 全缺。
    expect(score).toBeNull();
    expect(factors.every((f) => f.weight === 0)).toBe(true);
  });

  it('部分缺数据：有效因子按比例接管权重', () => {
    // 延迟缺失；检索 93 分、满意度 100 分。
    const { score, factors } = computeHealthScore(
      retrieval(0.0333, null),
      feedback(0.9),
      DEFAULT_HEALTH_THRESHOLDS,
    );
    const latencyFactor = factors.find((f) => f.key === 'latency')!;
    expect(latencyFactor.score).toBeNull();
    expect(latencyFactor.weight).toBe(0);
    // 检索/满意度权重从 .7 扩到 1（各 ~.43/.57）。
    expect(score!).toBeGreaterThan(90);
  });
});
