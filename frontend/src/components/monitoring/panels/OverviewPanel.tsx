import { useMemo } from 'react';
import type { TimeRangeQuery } from '../../../types/monitoring';
import EChart from '../../shared/EChart';
import AlertsSummaryCard from '../AlertsSummaryCard';
import DataGate from '../DataGate';
import { formatCount, formatMs, formatPct } from '../formatters';
import HealthScoreCard from '../HealthScoreCard';
import MetricPanel from '../MetricPanel';
import {
  isIntradayQuery,
  useMonitoringSummaryQuery,
  useMonitoringTimeseriesQuery,
} from '../useMonitoringQueries';
import { SLO_TARGET_PCT, useOverviewDerived } from '../useOverviewDerived';
import { useTranslation } from 'react-i18next';

interface Props {
  timeQuery: TimeRangeQuery;
}

/** 检索日志下钻契约：预设窗口带 hours；自定义范围不带区间参数。 */
function logsHref(timeQuery: TimeRangeQuery, emptyOnly = false): string {
  const base = timeQuery.since
    ? '/retrieval-logs'
    : `/retrieval-logs?hours=${timeQuery.window_hours}`;
  if (!emptyOnly) return base;
  return base.includes('?') ? `${base}&empty=1` : `${base}?empty=1`;
}

/**
 * 总览 Tab：回答"系统健不健康"——健康分 + 四张核心趋势
 * （检索量 / 空召回 / 好评率 / 延迟分位带）+ 告警规则摘要。
 * 数据获取在本组件，图形编码在 useOverviewDerived。
 */
export default function OverviewPanel({ timeQuery }: Props) {
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

  const {
    volumeChartOption,
    goodRateChartOption,
    emptyRecallChartOption,
    latencyChartOption,
    totalDelta,
    emptyRecallDelta,
    goodRateDelta,
    latDelta,
    sloPct,
  } = useOverviewDerived({ points, prevPoints, intraday });

  const retryAll = () => {
    void refetch();
    void tsRefetch();
  };
  const ready = data != null && ts != null;

  // 预设窗口后端返回对齐上期 → 环比位恒在（徽章或无基线占位）；
  // 自定义范围无对比概念 → 环比位整体隐藏。
  const comparisonAvailable = prevPoints != null;

  return (
    <DataGate
      loading={isLoading || tsLoading}
      error={isError || tsError}
      ready={ready}
      onRetry={retryAll}
    >
      {data && ts ? (
        <div className="flex flex-col gap-3">
          <div
            className="grid grid-cols-1 gap-3 lg:grid-cols-[280px_minmax(0,1fr)_minmax(0,1fr)]"
            data-testid="retrieval-section"
          >
            <div className="lg:row-span-2">
              <HealthScoreCard health={data.health_score} />
            </div>

            <MetricPanel
              title={t('monitoring.chartVolumeTitle')}
              value={
                data.retrieval.total > 0
                  ? formatCount(data.retrieval.total)
                  : '—'
              }
              delta={totalDelta}
              deltaGoodWhenUp={true}
              comparisonAvailable={comparisonAvailable}
              href={logsHref(timeQuery)}
              testId="chart-volume"
            >
              <EChart
                option={volumeChartOption}
                height={200}
                ariaLabel={t('monitoring.chartVolumeTitle')}
                testId="chart-volume-canvas"
              />
            </MetricPanel>

            <MetricPanel
              title={t('monitoring.chartEmptyRecallTitle')}
              value={formatPct(
                data.retrieval.total > 0
                  ? data.retrieval.empty_recall_rate
                  : null,
              )}
              delta={emptyRecallDelta}
              deltaGoodWhenUp={false}
              comparisonAvailable={comparisonAvailable}
              href={logsHref(timeQuery, true)}
              testId="chart-emptyrecall-panel"
            >
              <EChart
                option={emptyRecallChartOption}
                height={200}
                ariaLabel={t('monitoring.chartEmptyRecallTitle')}
                testId="chart-emptyrecall"
              />
            </MetricPanel>

            <MetricPanel
              title={t('monitoring.chartGoodRateTitle')}
              value={formatPct(data.feedback.good_ratio)}
              delta={goodRateDelta}
              deltaGoodWhenUp={true}
              comparisonAvailable={comparisonAvailable}
              testId="chart-goodrate-panel"
            >
              <EChart
                option={goodRateChartOption}
                height={200}
                ariaLabel={t('monitoring.chartGoodRateTitle')}
                testId="chart-goodrate"
              />
            </MetricPanel>

            <MetricPanel
              title={t('monitoring.chartLatencyTitle')}
              value={formatMs(data.retrieval.latency_p50_ms)}
              delta={latDelta}
              deltaGoodWhenUp={false}
              comparisonAvailable={comparisonAvailable}
              substat={`P95 ${formatMs(
                data.retrieval.latency_p95_ms,
              )} · ${t('monitoring.sloAttain')} ${sloPct ?? '—'}%`}
              substatDanger={sloPct != null && sloPct < SLO_TARGET_PCT}
              href={logsHref(timeQuery)}
              testId="chart-latency-panel"
            >
              <EChart
                option={latencyChartOption}
                height={200}
                ariaLabel={t('monitoring.chartLatencyTitle')}
                testId="chart-latency"
              />
            </MetricPanel>
          </div>

          <AlertsSummaryCard alerts={data.alerts} />
        </div>
      ) : null}
    </DataGate>
  );
}
