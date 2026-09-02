import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { fetchRootCauses } from '../../api/client/monitoring';
import type { ReviewRootCause, TimeRangeQuery } from '../../types/monitoring';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import EChart, { type EChartsOption } from '../shared/EChart';
import { rootCauseParetoOption } from './chartOptions';

interface Props {
  timeQuery: TimeRangeQuery;
}

const CAUSE_I18N_KEY: Record<ReviewRootCause, string> = {
  retrieval_miss: 'monitoring.review.causeRetrievalMiss',
  wrong_answer: 'monitoring.review.causeWrongAnswer',
  bad_format: 'monitoring.review.causeBadFormat',
  other: 'monitoring.review.causeOther',
};

/**
 * 差评根因帕累托：横向条形 + 累计占比线，头部展示分诊状态混。
 * 数据源：/monitoring/root-causes（feedback_reviews 聚合）。
 */
export default function RootCausePareto({ timeQuery }: Props) {
  const { t } = useTranslation();
  const rangeKey = timeQuery.since ? `${timeQuery.since}-${timeQuery.until}` : timeQuery.window_hours;
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['monitoring-root-causes', rangeKey],
    queryFn: () => fetchRootCauses(timeQuery),
  });

  const pareto = useMemo(() => {
    if (!data) return null;
    const sorted = [...data.causes].sort((a, b) => b.count - a.count);
    const total = sorted.reduce((sum, c) => sum + c.count, 0);
    let running = 0;
    return {
      categories: sorted.map((c) => t(CAUSE_I18N_KEY[c.cause])),
      counts: sorted.map((c) => c.count),
      cumulativePct: sorted.map((c) => {
        running += c.count;
        return total > 0 ? Math.round((running / total) * 1000) / 10 : 0;
      }),
      total,
    };
  }, [data, t]);

  const option: EChartsOption | null = useMemo(() => {
    if (!pareto) return null;
    return rootCauseParetoOption({
      categories: pareto.categories,
      counts: pareto.counts,
      cumulativePct: pareto.cumulativePct,
      labels: {
        count: t('monitoring.pareto.count'),
        cumulative: t('monitoring.pareto.cum'),
      },
    });
  }, [pareto, t]);

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-5">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="m-0 text-sm font-medium text-[var(--color-text-primary)]">
          {t('monitoring.pareto.title')}
        </h3>
        {data && (
          <span
            className="font-mono text-[10px] text-[var(--color-text-muted)]"
            data-testid="pareto-triage-mix"
          >
            {t('monitoring.review.statusPending')} {data.pending} ·{' '}
            {t('monitoring.review.statusResolved')} {data.resolved} ·{' '}
            {t('monitoring.review.statusDismissed')} {data.dismissed}
          </span>
        )}
      </div>
      {isError ? (
        <EmptyState
          title={t('monitoring.loadFailed')}
          action={
            <button
              type="button"
              className="px-3 py-1.5 rounded-md text-sm cursor-pointer border-none bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
              onClick={() => void refetch()}
            >
              {t('common.retry')}
            </button>
          }
          centered
        />
      ) : isLoading || !data || !option ? (
        <LoadingState centered />
      ) : pareto!.total === 0 ? (
        <EmptyState
          title={t('monitoring.noData')}
          description={t('monitoring.pareto.emptyDesc')}
          centered
        />
      ) : (
        <EChart
          option={option}
          height={280}
          ariaLabel={t('monitoring.pareto.title')}
          testId="chart-pareto"
        />
      )}
    </div>
  );
}
