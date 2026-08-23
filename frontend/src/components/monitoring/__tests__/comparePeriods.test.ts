import { periodDelta } from '../chartOptions';

describe('periodDelta（真·周期环比）', { tags: ['unit'] }, () => {
  it('量类求和：本期 vs 上期', () => {
    expect(periodDelta([10, 20], [10, 10], 'sum')).toEqual({
      pct: 50,
      up: true,
    });
    expect(periodDelta([5], [10], 'sum')).toEqual({ pct: -50, up: false });
  });

  it('均值类取平均', () => {
    expect(periodDelta([100, 200], [300, 300], 'avg')).toEqual({
      pct: -50,
      up: false,
    });
  });

  it('上期无基线（空/零/非有限值）→ null 不展示涨跌', () => {
    expect(periodDelta([1, 2, 3], [], 'sum')).toBeNull();
    expect(periodDelta([5], [0], 'sum')).toBeNull();
    expect(periodDelta([5], [Number.NaN], 'avg')).toBeNull();
  });

  it('过滤非有限值后仍可计算', () => {
    // 空桶以 NaN 占位时应被剔除。
    expect(
      periodDelta(
        [4, Number.NaN],
        [2, Number.NaN],
        'avg',
      ),
    ).toEqual({ pct: 100, up: true });
  });
});
