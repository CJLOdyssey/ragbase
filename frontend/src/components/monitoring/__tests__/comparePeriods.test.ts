import { periodDelta, ratioDelta, weightedDelta } from '../chartOptions';

describe('periodDelta（总量环比·sum）', { tags: ['unit'] }, () => {
  it('本期 vs 上期', () => {
    expect(periodDelta([10, 20], [10, 10])).toEqual({ pct: 50, up: true });
    expect(periodDelta([5], [10])).toEqual({ pct: -50, up: false });
  });

  it('上期无基线（空/零/非有限值）→ null 不展示涨跌', () => {
    expect(periodDelta([1, 2, 3], [])).toBeNull();
    expect(periodDelta([5], [0])).toBeNull();
    expect(periodDelta([5], [Number.NaN])).toBeNull();
  });
});

describe('ratioDelta（比率环比·ratio-of-sums）', { tags: ['unit'] }, () => {
  it('分子分母分别跨桶加总后相除', () => {
    // cur = 3/40 = 7.5%；prev = 4/28 ≈ 14.286% → -47.5%
    const out = ratioDelta([2, 1], [10, 30], [1, 3], [8, 20]);
    expect(out).not.toBeNull();
    expect(out!.pct).toBeCloseTo(-47.5, 6);
    expect(out!.up).toBe(false);
  });

  it('零样本桶不入分母（回归：修复旧 ?? 0 稀释缺陷）', () => {
    // 第二桶 0 检索：旧算法按 0% 计入平均 → 25%；正确值 = 5/10 = 50% → +400%。
    expect(ratioDelta([5, 0], [10, 0], [1], [10])).toEqual({
      pct: 400,
      up: true,
    });
  });

  it('任一侧无正分母基线（全空桶/零）→ null', () => {
    expect(ratioDelta([1], [10], [], [])).toBeNull();
    expect(ratioDelta([1], [10], [0], [0])).toBeNull();
    expect(ratioDelta([], [], [1], [10])).toBeNull();
  });
});

describe('weightedDelta（均值环比·样本量加权）', { tags: ['unit'] }, () => {
  it('按权重加权而非等权平均', () => {
    // cur = (300×10 + 500×30)/40 = 450；prev = 200 → +125%
    expect(weightedDelta([300, 500], [10, 30], [200], [10])).toEqual({
      pct: 125,
      up: true,
    });
  });

  it('null 值与零权重桶被剔除', () => {
    // cur = 500；prev = 250 → +100%
    expect(
      weightedDelta([null, 500], [0, 30], [Number.NaN, 250], [99, 10]),
    ).toEqual({ pct: 100, up: true });
  });

  it('任一侧无有效样本或上期基线 ≤0 → null', () => {
    expect(weightedDelta([100], [0], [100], [10])).toBeNull();
    expect(weightedDelta([100], [10], [], [])).toBeNull();
    expect(weightedDelta([100], [10], [0], [10])).toBeNull();
  });
});
