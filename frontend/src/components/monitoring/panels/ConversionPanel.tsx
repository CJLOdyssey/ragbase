import { useMemo } from 'react';
import type { TimeRangeQuery } from '../../../types/monitoring';
import EChart, { type EChartsOption } from '../../shared/EChart';
import { STATUS_COLORS } from '../../shared/statusColors';
import { lineTrendOption, weightedDelta } from '../chartOptions';
import DataGate from '../DataGate';
import FeedbackComposition from '../FeedbackComposition';
import MetricPanel from '../MetricPanel';
import RetrievalFunnel from '../RetrievalFunnel';
import {
  isIntradayQuery,
  useMonitoringSummaryQuery,
  useMonitoringTimeseriesQuery,
} from '../useMonitoringQueries';
import { useTranslation } from 'react-i18next';

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

  // 均值型环比：按检索次数加权，零样本桶不入权重（与总览页同一聚合语义）。
  const hitDelta = useMemo(
    () =>
      weightedDelta(
        points.map((p) => p.avg_hits),
        points.map((p) => p.retrievals),
        (prevPoints ?? []).map((p) => p.avg_hits),
        (prevPoints ?? []).map((p) => p.retrievals),
      ),
    [points, prevPoints],
  );

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
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 items-stretch">
            <RetrievalFunnel summary={data} />
            <MetricPanel
              title={t('monitoring.chartHitsTitle')}
              value={
                data.retrieval.avg_hit_count != null && data.retrieval.total > 0
                  ? data.retrieval.avg_hit_count.toFixed(1)
                  : '—'
              }
              delta={hitDelta}
              deltaGoodWhenUp={true}
              comparisonAvailable={prevPoints != null}
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

          <div className="lg:col-span-2">
            <FeedbackComposition points={points} intraday={intraday} />
          </div>
        </>
      ) : null}
    </DataGate>
  );
}
