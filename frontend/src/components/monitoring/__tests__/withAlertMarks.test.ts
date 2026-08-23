import type { EChartsOption } from '../../shared/EChart';
import type { MonitoringPoint } from '../../../types/monitoring';
import { withAlertMarks, type AlertMarkSpec } from '../chartOptions';

const POINTS: MonitoringPoint[] = [
  {
    ts: '2026-08-23T00:00:00+00:00',
    retrievals: 10,
    empty_count: 5, // 50% > 15% → 突破
    avg_hits: 1,
    avg_latency_ms: 100,
    latency_p50_ms: 80,
    latency_p95_ms: 200,
    good: 1,
    bad: 1,
  },
  {
    ts: '2026-08-23T01:00:00+00:00',
    retrievals: 10,
    empty_count: 0,
    avg_hits: 3,
    avg_latency_ms: 100,
    latency_p50_ms: 90,
    latency_p95_ms: 150,
    good: 2,
    bad: 0,
  },
];

function baseOption(): EChartsOption {
  return {
    series: [
      { name: 'bars', type: 'bar', data: [] },
      { name: 'line', type: 'line', data: [] },
    ],
  } as EChartsOption;
}

const SPEC: AlertMarkSpec = {
  targetSeriesName: 'bars',
  valueAt: (p) => p.retrievals,
  breached: (p) => p.retrievals > 0 && p.empty_count / p.retrievals > 0.15,
  label: '阈值突破',
};

describe('withAlertMarks（组合式装饰器）', { tags: ['unit'] }, () => {
  it('无突破桶时原样返回，不注入 markPoint', () => {
    const option = baseOption();
    const out = withAlertMarks(option, [POINTS[1]], SPEC);
    expect(out).toBe(option);
    expect((out.series as Array<Record<string, unknown>>)[0].markPoint).toBeUndefined();
  });

  it('只向目标系列追加 markPoint，其他系列不动', () => {
    const out = withAlertMarks(baseOption(), POINTS, SPEC);
    const series = out.series as Array<Record<string, unknown>>;
    const bars = series.find((s) => s.name === 'bars')!;
    const line = series.find((s) => s.name === 'line')!;
    const mp = bars.markPoint as { data: Array<{ coord: [string, number] }> };
    expect(mp.data).toHaveLength(1);
    expect(mp.data[0].coord).toEqual([POINTS[0].ts, 10]);
    expect(line.markPoint).toBeUndefined();
  });

  it('保留目标系列已有 markPoint 数据（追加而非覆盖）', () => {
    const option = baseOption();
    (option.series as Array<Record<string, unknown>>)[0].markPoint = {
      data: [{ coord: ['2026-08-22T00:00:00+00:00', 1] }],
    };
    const out = withAlertMarks(option, POINTS, SPEC);
    const mp = (out.series as Array<Record<string, unknown>>)[0]
      .markPoint as { data: unknown[] };
    expect(mp.data).toHaveLength(2);
  });

  it('目标系列不存在时不改动 option', () => {
    const option = baseOption();
    const out = withAlertMarks(option, POINTS, { ...SPEC, targetSeriesName: 'ghost' });
    expect(out).toBe(option);
  });

  it('valueAt 返回 null 的突破桶不打点', () => {
    const option = baseOption();
    const out = withAlertMarks(option, POINTS, {
      ...SPEC,
      valueAt: () => null,
    });
    expect(out).toBe(option);
    const series = out.series as Array<Record<string, unknown>>;
    expect(series[0].markPoint).toBeUndefined();
  });
});
