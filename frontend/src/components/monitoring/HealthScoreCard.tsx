import { useMemo } from 'react';
import EChart from '../shared/EChart';
import { STATUS_COLORS } from '../shared/statusColors';
import { useTranslation } from 'react-i18next';
import type {
  HealthFactorKey,
  HealthScorePayload,
} from '../../types/monitoring';
import { healthGaugeOption, healthTrendOption } from './chartOptions';
import { useHealthScoreHistoryQuery } from './useMonitoringQueries';

interface Props {
  /** 服务端 /monitoring/summary 返回的错误预算健康分。 */
  health: HealthScorePayload;
}

export function gradeColor(score: number | null): string {
  if (score == null) return 'var(--color-text-muted)';
  if (score >= 80) return STATUS_COLORS.green;
  if (score >= 60) return STATUS_COLORS.amber;
  return STATUS_COLORS.red;
}

const FACTOR_I18N_KEY: Record<HealthFactorKey, string> = {
  retrieval: 'monitoring.health.factorRetrieval',
  latency: 'monitoring.health.factorLatency',
  satisfaction: 'monitoring.health.factorSatisfaction',
};

/**
 * 综合健康分竖卡（Datadog service health 式）：
 * 大仪表（服务端错误预算模型）+ 因子贡献条 + 近 7 天快照 sparkline。
 */
export default function HealthScoreCard({ health }: Props) {
  const { t } = useTranslation();
  const { score, factors } = health;
  const color = gradeColor(score);

  // 近 7 天小时级快照；无数据时静默隐藏趋势区。
  const { data: history } = useHealthScoreHistoryQuery(168);
  const historyPoints = useMemo(() => history?.points ?? [], [history]);

  const option = useMemo(
    () =>
      healthGaugeOption({
        score,
        color,
        label: t('monitoring.health.title'),
      }),
    [score, color, t],
  );

  const trendOption = useMemo(
    () => healthTrendOption({ points: historyPoints }),
    [historyPoints],
  );

  return (
    <div
      className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-5 h-full flex flex-col"
      data-testid="health-score-card"
    >
      <div className="text-xs text-[var(--color-text-muted)]">
        {t('monitoring.health.title')}
      </div>
      <EChart
        option={option}
        height={150}
        className="mt-1"
        ariaLabel={`${t('monitoring.health.title')} ${score ?? '—'}`}
        testId="health-gauge"
      />
      <div className="flex flex-1 flex-col justify-center gap-3 mt-2 min-w-0">
        {factors.map((f) => (
          <div key={f.key} data-testid={`health-factor-${f.key}`}>
            <div className="mb-1 flex items-baseline justify-between gap-2 font-mono text-[10px] text-[var(--color-text-muted)]">
              <span>{t(FACTOR_I18N_KEY[f.key])}</span>
              <span className="tabular-nums">
                {f.score == null ? '—' : f.score}
                {' · '}
                {Math.round(f.weight * 100)}%
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-[var(--color-surface-elevated)] overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${f.score ?? 0}%`,
                  background:
                    f.score == null
                      ? 'var(--color-surface-hover)'
                      : gradeColor(f.score),
                }}
              />
            </div>
          </div>
        ))}
        {historyPoints.length > 1 ? (
          <div data-testid="health-trend">
            <div className="font-mono text-[9px] text-[var(--color-text-muted)] mb-0.5">
              {t('monitoring.health.trendTitle')}
            </div>
            <EChart
              option={trendOption}
              height={56}
              ariaLabel={t('monitoring.health.trendTitle')}
              testId="health-trend-canvas"
            />
          </div>
        ) : null}
        <div className="font-mono text-[9px] leading-relaxed text-[var(--color-text-muted)]">
          {t('monitoring.health.budgetHint', {
            w1: Math.round(
              (factors.find((f) => f.key === 'retrieval')?.weight ?? 0) * 100,
            ),
            w2: Math.round(
              (factors.find((f) => f.key === 'latency')?.weight ?? 0) * 100,
            ),
            w3: Math.round(
              (factors.find((f) => f.key === 'satisfaction')?.weight ?? 0) *
                100,
            ),
          })}
        </div>
      </div>
    </div>
  );
}
