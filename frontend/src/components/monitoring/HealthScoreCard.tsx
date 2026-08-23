import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import type { FeedbackMetrics, RetrievalMetrics } from '../../types/monitoring';
import EChart from '../shared/EChart';
import { STATUS_COLORS } from '../shared/statusColors';
import { healthGaugeOption } from './chartOptions';
import {
  computeHealthScore,
  DEFAULT_HEALTH_THRESHOLDS,
  HEALTH_WEIGHTS,
  type HealthFactorKey,
} from './healthScore';

interface Props {
  retrieval: RetrievalMetrics;
  feedback: FeedbackMetrics;
}

function gradeColor(score: number | null): string {
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
 * 顶部大仪表 + 底部三因子贡献条，与相邻趋势图等高构成总览行左栏。
 */
export default function HealthScoreCard({ retrieval, feedback }: Props) {
  const { t } = useTranslation();
  const { score, factors } = useMemo(
    () => computeHealthScore(retrieval, feedback, DEFAULT_HEALTH_THRESHOLDS),
    [retrieval, feedback],
  );
  const color = gradeColor(score);

  const option = useMemo(
    () =>
      healthGaugeOption({
        score,
        color,
        label: t('monitoring.health.title'),
      }),
    [score, color, t],
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
        <div className="font-mono text-[9px] leading-relaxed text-[var(--color-text-muted)]">
          {t('monitoring.health.weightsHint', {
            w1: Math.round(HEALTH_WEIGHTS.retrieval * 100),
            w2: Math.round(HEALTH_WEIGHTS.latency * 100),
            w3: Math.round(HEALTH_WEIGHTS.satisfaction * 100),
          })}
        </div>
      </div>
    </div>
  );
}
