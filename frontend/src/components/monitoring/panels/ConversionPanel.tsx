import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { STATUS_COLORS } from '../../shared/statusColors';
import type { TimeRangeQuery } from '../../../types/monitoring';
import EChart, { type EChartsOption } from '../../shared/EChart';
import { lineTrendOption, periodDelta } from '../chartOptions';
import DataGate from '../DataGate';
import MetricPanel from '../MetricPanel';
import RetrievalFunnel from '../RetrievalFunnel';
import {
  isIntradayQuery,
  useMonitoringSummaryQuery,
  useMonitoringTimeseriesQuery,
} from '../useMonitoringQueries';

interface Props {
  timeQuery: TimeRangeQuery;
}

/** 转化分析 Tab：回答"流量在哪一环漏掉"——检索转化漏斗 + 平均命中趋势。 */
export default function ConversionPanel({ timeQuery }: Props) {
  const { t } = useTranslation();
  const intraday = isIntradayQuery(timeQuery);

  const { data, isLoading, isError, refetch } =
    useMonitoringSummaryQuery(timeQuery);
  const {
    data: ts,
    isLoading: tsLoading,
    isError: tsError,
    refetch: tsRefetch,
  } = useMonitoringTimeseriesQuery(timeQuery);

  const points = useMemo(() => ts?.points ?? [], [ts]);
  const prevPoints = ts?.previous_points ?? null;

  const hitSeries = points.map((p) => p.avg_hits ?? 0);
  const prevHit = prevPoints?.map((p) => p.avg_hits ?? 0) ?? [];
  const hitDelta = periodDelta(hitSeries, prevHit, 'avg');

  const hitsChartOption: EChartsOption = useMemo(
    () =>
      lineTrendOption({
        points,
        prevPoints,
        pick: (p) => p.avg_hits,
        color: STATUS_COLORS.blue,
        labels: {
          series: t('monitoring.kpiAvgHit'),
          prevPeriod: t('monitoring.prevPeriod'),
        },
        formatValue: (v) => v.toFixed(1),
        intraday,
      }),
    [points, prevPoints, intraday, t],
  );

  const retryAll = () => {
    void refetch();
    void tsRefetch();
  };

  return (
    <DataGate
      loading={isLoading || tsLoading}
      error={isError || tsError}
      ready={data != null && ts != null}
      onRetry={retryAll}
    >
      {data && ts ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 items-stretch">
          <RetrievalFunnel summary={data} />
          <MetricPanel
            title={t('monitoring.chartHitsTitle')}
            value={
              data.retrieval.avg_hit_count != null &&
              data.retrieval.total > 0
                ? data.retrieval.avg_hit_count.toFixed(1)
                : '—'
            }
            delta={hitDelta}
            deltaGoodWhenUp={true}
            testId="chart-hits-panel"
          >
            <EChart
              option={hitsChartOption}
              height={240}
              ariaLabel={t('monitoring.chartHitsTitle')}
              testId="chart-hits"
            />
          </MetricPanel>
        </div>
      ) : null}
    </DataGate>
  );
}
