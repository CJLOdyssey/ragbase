import type { MonitoringPoint } from '../../../types/monitoring';
import type { EChartsOption } from '../../shared/EChart';
import { withBreachRegions, withBreachTint } from '../chartOptions';

function point(
  ts: string,
  over: Partial<MonitoringPoint> = {},
): MonitoringPoint {
  return {
    ts,
    retrievals: 10,
    empty_count: 0,
    avg_hits: 1,
    avg_latency_ms: 100,
    latency_p50_ms: 80,
    latency_p95_ms: 200,
    latency_p99_ms: 300,
    good: 1,
    bad: 0,
    ...over,
  };
}

/** 空召回率：50% > 15% 越线；其余桶正常。 */
const EMPTY_RATE_BREACH = (p: MonitoringPoint) =>
  p.retrievals > 0 && p.empty_count / p.retrievals > 0.15;

function barsOption(data: Array<[string, number]>): EChartsOption {
  return {
    series: [
      { name: 'bars', type: 'bar', data },
      { name: 'other', type: 'line', data: [] },
    ],
  } as EChartsOption;
}

describe('withBreachTint（越线项本体着色）', { tags: ['unit'] }, () => {
  const SPEC = {
    targetSeriesName: 'bars',
    valueAt: (p: MonitoringPoint) => (p.empty_count / p.retrievals) * 100,
    breached: EMPTY_RATE_BREACH,
    color: '#ff4444',
  };

  it('无越线桶时原样返回，不改动任何数据', () => {
    const option = barsOption([
      ['2026-08-23T00:00:00+00:00', 5],
      ['2026-08-23T01:00:00+00:00', 0],
    ]);
    const out = withBreachTint(
      option,
      [
        point('2026-08-23T00:00:00+00:00', { empty_count: 1 }),
        point('2026-08-23T01:00:00+00:00'),
      ],
      SPEC,
    );
    expect(out).toBe(option);
    expect((out.series as Array<Record<string, unknown>>)[0].data).toHaveLength(
      2,
    );
  });

  it('只重写目标系列的越线数据项为 { value, itemStyle }，其他项与其他系列不动', () => {
    const ts0 = '2026-08-23T00:00:00+00:00';
    const ts1 = '2026-08-23T01:00:00+00:00';
    const out = withBreachTint(
      barsOption([
        [ts0, 50],
        [ts1, 0],
      ]),
      [point(ts0, { empty_count: 5 }), point(ts1)],
      SPEC,
    );
    const series = out.series as Array<Record<string, unknown>>;
    const data = series[0].data as Array<unknown>;
    expect(data[0]).toEqual({
      value: [ts0, 50],
      itemStyle: { color: '#ff4444' },
    });
    expect(data[1]).toEqual([ts1, 0]);
    expect(series[1].data).toEqual([]);
  });

  it('目标系列不存在时不改动 option', () => {
    const option = barsOption([]);
    const out = withBreachTint(
      option,
      [point('2026-08-23T00:00:00+00:00', { empty_count: 5 })],
      {
        ...SPEC,
        targetSeriesName: 'ghost',
      },
    );
    expect(out).toBe(option);
  });

  it('valueAt 返回 null 的越线桶不着色', () => {
    const option = barsOption([['2026-08-23T00:00:00+00:00', 50]]);
    const out = withBreachTint(
      option,
      [point('2026-08-23T00:00:00+00:00', { empty_count: 5 })],
      { ...SPEC, valueAt: () => null },
    );
    expect(out).toBe(option);
  });
});

describe('withBreachRegions（连续越线时段底纹）', { tags: ['unit'] }, () => {
  const p95Breached = (p: MonitoringPoint) =>
    p.latency_p95_ms != null && p.latency_p95_ms > 8000;

  it('连续越线桶归并为一个区间，离散桶各自成区间', () => {
    const a = point('2026-08-23T00:00:00+00:00', { latency_p95_ms: 9000 });
    const b = point('2026-08-23T01:00:00+00:00', { latency_p95_ms: 9500 });
    const c = point('2026-08-23T02:00:00+00:00', { latency_p95_ms: 5000 });
    const d = point('2026-08-23T03:00:00+00:00', { latency_p95_ms: 8100 });

    const option = barsOption([]);
    const out = withBreachRegions(option, 'bars', [a, b, c, d], {
      breached: p95Breached,
    });
    const target = (out.series as Array<Record<string, unknown>>)[0];
    const markArea = target.markArea as {
      data: Array<[unknown, unknown]>;
      silent: boolean;
      itemStyle: { color: string };
    };
    expect(markArea.silent).toBe(true);
    expect(markArea.itemStyle.color).toContain('rgba(255,68,68');
    expect(markArea.data).toEqual([
      [{ xAxis: a.ts }, { xAxis: b.ts }],
      [{ xAxis: d.ts }, { xAxis: d.ts }],
    ]);
  });

  it('无越线时段时原样返回', () => {
    const option = barsOption([]);
    const out = withBreachRegions(
      option,
      'bars',
      [point('2026-08-23T00:00:00+00:00', { latency_p95_ms: 1000 })],
      { breached: p95Breached },
    );
    expect(out).toBe(option);
  });

  it('追加到已有 markArea 而非覆盖', () => {
    const option = barsOption([]);
    (option.series as Array<Record<string, unknown>>)[0].markArea = {
      data: [[{ xAxis: 'old-a' }, { xAxis: 'old-b' }]],
    };
    const out = withBreachRegions(
      option,
      'bars',
      [point('2026-08-23T00:00:00+00:00', { latency_p95_ms: 9000 })],
      { breached: p95Breached },
    );
    const markArea = (out.series as Array<Record<string, unknown>>)[0]
      .markArea as { data: unknown[] };
    expect(markArea.data).toHaveLength(2);
  });

  it('目标系列不存在时不改动 option', () => {
    const option = barsOption([]);
    const out = withBreachRegions(
      option,
      'ghost',
      [point('2026-08-23T00:00:00+00:00', { latency_p95_ms: 9000 })],
      { breached: p95Breached },
    );
    expect(out).toBe(option);
  });
});
