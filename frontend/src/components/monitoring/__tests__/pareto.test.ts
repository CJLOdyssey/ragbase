import { rootCauseParetoOption } from '../chartOptions';

const SPEC = {
  categories: ['检索不准', '回答错误', '格式问题', '其他'],
  counts: [12, 6, 2, 1],
  cumulativePct: [57.1, 85.7, 95.2, 100],
  labels: { count: '次数', cumulative: '累计占比' },
};

describe(
  'rootCauseParetoOption（P1：排序条 + 累计数字标签）',
  { tags: ['unit'] },
  () => {
    it('单一条形系列：无累计折线、无顶部 % 轴、无 markLine', () => {
      const opt = rootCauseParetoOption(SPEC);
      const series = opt.series as Array<Record<string, unknown>>;
      expect(series).toHaveLength(1);
      expect(series[0].type).toBe('bar');
      expect(series[0].markLine).toBeUndefined();
      expect(opt.xAxis).toEqual(expect.objectContaining({ type: 'value' }));
      // 单系列无需图例。
      expect(opt.legend).toBeUndefined();
    });

    it('条尾标签输出「次数 · 累计%」，整数百分比不带小数位', () => {
      const opt = rootCauseParetoOption(SPEC);
      const label = ((opt.series as Array<Record<string, unknown>>)[0].label ??
        {}) as { formatter: (p: unknown) => string };
      expect(label.formatter({ value: 6, dataIndex: 1 })).toBe('6 · 85.7%');
      expect(label.formatter({ value: 1, dataIndex: 3 })).toBe('1 · 100%');
    });

    it('item tooltip 输出类目名+次数+累计%，绝不出现 NaN', () => {
      const opt = rootCauseParetoOption(SPEC);
      const tooltip = opt.tooltip as {
        formatter: (p: unknown) => string;
      } & Record<string, unknown>;
      expect(tooltip.trigger).toBe('item');
      const html = tooltip.formatter({
        name: '回答错误',
        value: 6,
        dataIndex: 1,
      });
      expect(html).toContain('回答错误');
      expect(html).toContain('<b>6</b>');
      expect(html).toContain('85.7%');
      expect(html.toLowerCase()).not.toContain('nan');
    });
  },
);
