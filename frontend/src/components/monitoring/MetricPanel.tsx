import type { ReactNode } from 'react';
import { TrendingDown, TrendingUp } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import type { KpiDelta } from './chartOptions';

function Substat({ text, danger }: { text: string; danger: boolean }) {
  return (
    <div
      className={`mt-0.5 font-mono text-[10px] truncate ${
        danger ? 'text-[var(--color-danger)]' : 'text-[var(--color-text-muted)]'
      }`}
    >
      {text}
    </div>
  );
}

/**
 * 指标面板（small multiples 容器）：标题 + 当前值 + 周期环比徽章，
 * 图表本体由 children 提供 —— 数值与曲线同源，替代原 KPI 卡片。
 * comparisonAvailable=true 时环比位恒存在：有基线显示涨跌徽章，
 * 无基线显示灰色「—」占位（消除"时有时无"的不确定感）。
 */
/**
 * 环比徽章：有基线显示涨跌（绿=好/红=坏，极性由 deltaGoodWhenUp 决定）；
 * 无基线且视图存在对比语义时显示灰色「—」占位（hover 提示），否则不渲染。
 */
function DeltaBadge({
  delta,
  comparisonAvailable,
  deltaGoodWhenUp,
}: {
  delta: KpiDelta | null;
  comparisonAvailable: boolean;
  deltaGoodWhenUp: boolean;
}) {
  const { t } = useTranslation();
  if (delta === null || !Number.isFinite(delta.pct)) {
    return comparisonAvailable ? (
      <span
        className="font-mono text-[11px] tabular-nums text-[var(--color-text-muted)]"
        title={t('monitoring.deltaNoBaseline')}
      >
        —
      </span>
    ) : null;
  }
  const good = delta.up === deltaGoodWhenUp;
  const DeltaIcon = delta.up ? TrendingUp : TrendingDown;
  return (
    <span
      className={`inline-flex items-center gap-0.5 font-mono text-[11px] font-medium tabular-nums ${
        good ? 'text-[var(--color-success)]' : 'text-[var(--color-danger)]'
      }`}
      title={t('monitoring.deltaBaseline')}
    >
      <DeltaIcon size={11} />
      {`${Math.abs(delta.pct) >= 100 ? Math.round(Math.abs(delta.pct)) : Math.abs(delta.pct).toFixed(1)}%`}
    </span>
  );
}

export default function MetricPanel({
  title,
  value,
  delta = null,
  deltaGoodWhenUp = true,
  comparisonAvailable = false,
  substat,
  substatDanger = false,
  href,
  testId,
  children,
}: {
  title: string;
  value: string;
  delta?: KpiDelta | null;
  deltaGoodWhenUp?: boolean;
  /** 本视图是否存在周期对比语义（预设窗口才有；自定义范围整体隐藏环比位）。 */
  comparisonAvailable?: boolean;
  substat?: string;
  /** 副统计告警色调（如 SLO 燃烧率 ≥1× 时红色）。 */
  substatDanger?: boolean;
  href?: string;
  testId?: string;
  children: ReactNode;
}) {
  const header = (
    <div className="flex items-start justify-between gap-2">
      <div className="min-w-0">
        <h3 className="m-0 text-sm font-medium text-[var(--color-text-primary)] truncate">
          {title}
        </h3>
        {substat && <Substat text={substat} danger={substatDanger} />}
      </div>
      <div className="flex shrink-0 items-baseline gap-2">
        <DeltaBadge
          delta={delta}
          comparisonAvailable={comparisonAvailable}
          deltaGoodWhenUp={deltaGoodWhenUp}
        />
        <span
          className={`text-[22px] font-semibold leading-none tracking-[-0.02em] tabular-nums ${
            value === '—'
              ? 'text-[var(--color-text-muted)]'
              : 'text-[var(--color-text-primary)]'
          }`}
        >
          {value}
        </span>
      </div>
    </div>
  );

  return (
    <div
      className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-5"
      data-testid={testId}
    >
      {href ? (
        <Link
          to={href}
          className="block no-underline text-inherit transition-transform duration-150 hover:-translate-y-0.5"
        >
          {header}
        </Link>
      ) : (
        header
      )}
      <div className="mt-3">{children}</div>
    </div>
  );
}
