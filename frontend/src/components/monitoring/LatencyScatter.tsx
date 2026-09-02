import { useMemo } from 'react';
import EChart, { type EChartsOption } from '../shared/EChart';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { useTranslation } from 'react-i18next';
import type { TimeRangeQuery } from '../../types/monitoring';
import { latencyScatterOption } from './chartOptions';
import { useLatencyScatterQuery } from './useMonitoringQueries';

interface Props {
  timeQuery: TimeRangeQuery;
}

/** 延迟-命中散点图：x=命中数 y=延迟ms，红线=SLO 阈值，红点=超限请求。 */
export default function LatencyScatter({ timeQuery }: Props) {
  const { t } = useTranslation();
  const { data, isLoading, isError, refetch } =
    useLatencyScatterQuery(timeQuery);

  const option: EChartsOption | null = useMemo(() => {
    if (!data) return null;
    return latencyScatterOption({
      items: data.items.map((i) => ({
        ts: i.ts,
        hits: i.hits,
        latencyMs: i.latency_ms,
      })),
      sloMs: 8000,
      labels: {
        normal: t('monitoring.scatter.normal'),
        slow: t('monitoring.scatter.slow'),
        sloLine: t('monitoring.chartThreshold'),
        hits: t('monitoring.scatter.hits'),
        latency: t('monitoring.scatter.latency'),
      },
    });
  }, [data, t]);

  if (isLoading) return <LoadingState centered />;
  if (isError)
    return (
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
    );

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-5">
      <h3 className="m-0 mb-2 text-sm font-medium text-[var(--color-text-primary)]">
        {t('monitoring.chartScatterTitle')}
      </h3>
      {!data || data.items.length === 0 ? (
        <EmptyState
          title={t('monitoring.noData')}
          description={t('monitoring.chartScatterDesc')}
          centered
        />
      ) : (
        <EChart
          option={option!}
          height={240}
          ariaLabel={t('monitoring.chartScatterTitle')}
          testId="chart-latency-scatter"
        />
      )}
    </div>
  );
}
