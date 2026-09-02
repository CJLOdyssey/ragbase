import type { MonitoringPoint } from '../../../types/monitoring';

// ── 调色板（与 styles/tailwind-entry.css 的语义 token 同源）────────────────
export const ACCENT = '#6366f1'; // --color-accent
export const SUCCESS = '#34d399'; // --color-success
export const WARNING = '#f59e0b'; // --color-warning
export const DANGER = '#ff4444'; // --color-danger
export const MUTED_TEXT = '#8a8f98';
export const GRID_TEXT = 'rgba(138,143,152,0.14)';

/** #rrggbb → rgba(r,g,b,a)，渐变与指示线同源配色。 */
export function hexA(hex: string, alpha: number): string {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// ── 数值缩写（1500 → "1.5k"）────────────────────────────────────────────────
export const compact = (n: number): string => {
  const abs = Math.abs(n);
  const units: Array<[number, string]> = [
    [1e9, 'B'],
    [1e6, 'M'],
    [1e3, 'k'],
  ];
  for (const [size, suffix] of units) {
    if (abs >= size) {
      const v = n / size;
      const scaled = abs / size;
      const text = scaled >= 100 ? v.toFixed(0) : v.toFixed(1);
      return `${text.replace(/\.0$/, '')}${suffix}`;
    }
  }
  return Number.isInteger(n)
    ? String(n)
    : abs >= 10
      ? n.toFixed(0)
      : n.toFixed(1);
};

// ── 时间轴工具────────────────────────────────────────────────────────────────

/** 跨自然年或超半年的窗口，时间标签需带年份否则无法区分。 */
export function spansAcrossYear(firstTs: number, lastTs: number): boolean {
  const a = new Date(firstTs);
  const b = new Date(lastTs);
  return (
    a.getFullYear() !== b.getFullYear() ||
    b.getTime() - a.getTime() > 180 * 86400_000
  );
}

/** 一组时间点是否跨年或跨半年（主图/热力图年份标签开关）。 */
export function spansYear(points: MonitoringPoint[]): boolean {
  return (
    points.length > 1 &&
    spansAcrossYear(
      +new Date(points[0].ts),
      +new Date(points[points.length - 1].ts),
    )
  );
}

export function timeAxis(intraday: boolean, includeYear: boolean) {
  return {
    type: 'time' as const,
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: {
      color: MUTED_TEXT,
      fontSize: 10,
      hideOverlap: true,
      formatter: (ts: number) => {
        const d = new Date(ts);
        const pad = (n: number) => String(n).padStart(2, '0');
        if (includeYear)
          return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
        return intraday
          ? `${pad(d.getHours())}:${pad(d.getMinutes())}`
          : `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
      },
    },
  };
}

export function tooltipTime(
  tsMs: number | string,
  includeYear: boolean,
): string {
  const d = new Date(tsMs);
  const pad = (n: number) => String(n).padStart(2, '0');
  const date = includeYear
    ? `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
    : `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  return `${date} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// ── Tooltip / 图例公共配置────────────────────────────────────────────────────

export type SeriesFmtMap = Map<string, (v: number) => string>;

export function axisTooltip(fmts: SeriesFmtMap, includeYear: boolean) {
  return {
    trigger: 'axis' as const,
    axisPointer: {
      type: 'line' as const,
      lineStyle: { color: 'rgba(138,143,152,0.35)', width: 1 },
    },
    backgroundColor: 'rgba(17,21,28,0.96)',
    borderColor: 'rgba(255,255,255,0.08)',
    borderWidth: 1,
    padding: [8, 12],
    textStyle: { color: '#e6e9ef', fontSize: 12 },
    formatter: (params: unknown) => {
      const list = params as Array<{
        seriesName: string;
        value: [string, number | null];
        color?: string;
      }>;
      if (!list.length) return '';
      const time = tooltipTime(list[0].value[0], includeYear);
      const rows = list
        .map((p) => {
          const raw = p.value[1];
          const shown =
            raw === null || raw === undefined
              ? '—'
              : (fmts.get(p.seriesName) ?? compact)(raw);
          return `<div style="margin-top:4px"><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${p.color ?? MUTED_TEXT};margin-right:6px"></span>${p.seriesName}：<b>${shown}</b></div>`;
        })
        .join('');
      return `<div style="font-weight:600">${time}</div>${rows}`;
    },
  };
}

export const legendStyle = {
  top: 0,
  right: 0,
  icon: 'roundRect' as const,
  itemWidth: 10,
  itemHeight: 6,
  textStyle: { color: MUTED_TEXT, fontSize: 10 },
};

// ── Ghost 系列（上期虚线）────────────────────────────────────────────────────

export const GHOST_STYLE = {
  width: 1,
  type: 'dashed' as const,
  color: 'rgba(138,143,152,0.45)',
};

/**
 * 上期序列按 index 对齐到本期时间戳 —— ghost 虚线与真·环比共用此对齐。
 * 长度不一致时返回 undefined（宁缺毋错位）。
 */
export function alignedGhost(
  points: MonitoringPoint[],
  prevPoints: MonitoringPoint[] | null | undefined,
  pick: (p: MonitoringPoint) => number | null,
): Array<[string, number | null]> | undefined {
  if (!prevPoints || prevPoints.length !== points.length) return undefined;
  return points.map(
    (p, i) => [p.ts, pick(prevPoints[i])] as [string, number | null],
  );
}

export function ghostSeries(
  data: Array<[string, number | null]> | undefined,
  name: string,
) {
  if (!data) return null;
  return {
    name,
    type: 'line' as const,
    data,
    smooth: 0.25,
    showSymbol: false,
    connectNulls: false,
    silent: true,
    lineStyle: GHOST_STYLE,
    itemStyle: { color: GHOST_STYLE.color },
  };
}
