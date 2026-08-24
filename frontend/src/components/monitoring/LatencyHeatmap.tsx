import { useMemo } from 'react';
import EChart, { type EChartsOption } from '../shared/EChart';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { useTranslation } from 'react-i18next';
import type { TimeRangeQuery } from '../../types/monitoring';
import { latencyHeatmapOption } from './chartOptions';
import { useLatencyHeatmapQuery } from './useMonitoringQueries';

interface Props {
  timeQuery: TimeRangeQuery;
}

const BIN_LABELS = ['<0.5s', '0.5–1s', '1–2s', '2–4s', '4–8s', '>8s'];

/** 延迟分布热力图：时间 × 延迟区间的密度矩阵。 */
export default function LatencyHeatmap({ timeQuery }: Props) {
  const { t } = useTranslation();
  const { data, isLoading, isError, refetch } =
    useLatencyHeatmapQuery(timeQuery);

  const option: EChartsOption | null = useMemo(() => {
    if (!data) return null;
    return latencyHeatmapOption({
      points: data.points,
      binLabels: BIN_LABELS,
      intraday: false, // 热力图始终按天分桶
    });
  }, [data]);

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
        {t('monitoring.chartHeatmapTitle')}
      </h3>
      {!data || data.points.every((p) => p.counts.every((c) => c === 0)) ? (
        <EmptyState
          title={t('monitoring.noData')}
          description={t('monitoring.chartHeatmapDesc')}
          centered
        />
      ) : (
        <EChart
          option={option!}
          height={240}
          ariaLabel={t('monitoring.chartHeatmapTitle')}
          testId="chart-latency-heatmap"
        />
      )}
    </div>
  );
}
