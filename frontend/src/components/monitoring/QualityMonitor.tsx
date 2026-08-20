import { useState } from 'react';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { STATUS_COLORS, statusColor, withAlpha } from '../shared/statusColors';
import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  CheckCircle2,
  MessageSquare,
  ThumbsUp,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { fetchMonitoringSummary } from '../../api/client/monitoring';
import ChartCard from './ChartCard';
import KpiCard from './KpiCard';

const WINDOWS = [
  { hours: 24, key: 'monitoring.windowDay' },
  { hours: 24 * 7, key: 'monitoring.windowWeek' },
  { hours: 24 * 30, key: 'monitoring.windowMonth' },
  { hours: 0, key: 'monitoring.windowAll' },
] as const;

// Decorative sparkline series (no time-series endpoint is exposed by the
// backend summary; these mirror the prototype's illustrative curves).
const SPARK_TOTAL = [
  0.2, 0.35, 0.3, 0.5, 0.45, 0.6, 0.55, 0.7, 0.65, 0.8, 0.78, 0.9,
];
const SPARK_HIT = [
  0.1, 0.3, 0.25, 0.5, 0.4, 0.6, 0.55, 0.7, 0.65, 0.8, 0.75, 0.9,
];
const SPARK_LAT = [
  0.9, 0.7, 0.75, 0.5, 0.6, 0.4, 0.45, 0.3, 0.35, 0.2, 0.25, 0.15,
];
const SPARK_RATE = [
  0.2, 0.3, 0.5, 0.4, 0.6, 0.7, 0.65, 0.8, 0.75, 0.85, 0.9, 0.92,
];

function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(1)}%`;
}

function formatMs(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return `${value}ms`;
}

function formatCount(value: number): string {
  return new Intl.NumberFormat().format(value);
}

function formatAlertValue(code: string, value: number): string {
  if (code === 'good_ratio_low') return formatPct(value);
  if (code === 'empty_recall_high') return `${value.toFixed(1)}%`;
  return formatMs(Math.round(value));
}

export default function QualityMonitor() {
  const { t } = useTranslation();
  const [windowHours, setWindowHours] = useState(24);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['monitoring', windowHours],
    queryFn: () => fetchMonitoringSummary(windowHours),
  });

  return (
    <div className="flex flex-col h-full bg-[var(--color-surface)]">
      <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)]">
        <div>
          <h1 className="text-lg font-semibold text-[var(--color-text-primary)] m-0">
            {t('monitoring.title')}
          </h1>
          <p className="m-0 mt-0.5 text-xs text-[var(--color-text-muted)]">
            {t('monitoring.subtitle')}
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-1">
          {WINDOWS.map((w) => (
            <button
              key={w.hours}
              className={`px-3 py-1.5 rounded-md text-sm cursor-pointer border-none transition-colors duration-150 ${
                windowHours === w.hours
                  ? 'bg-[var(--color-accent)] text-[var(--color-text-on-accent)]'
                  : 'bg-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
              }`}
              onClick={() => setWindowHours(w.hours)}
              data-testid={`window-${w.hours}`}
            >
              {t(w.key)}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 p-6">
        {isError ? (
          <div className="flex flex-col items-center gap-3 py-10">
            <AlertTriangle
              size={24}
              className="text-[var(--color-warning, #d97706)]"
            />
            <span className="text-sm text-[var(--color-text-secondary)]">
              {t('monitoring.loadFailed')}
            </span>
            <button
              type="button"
              className="px-3 py-1.5 rounded-md text-sm cursor-pointer border-none bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
              onClick={() => void refetch()}
              data-testid="monitoring-retry"
            >
              {t('common.retry')}
            </button>
          </div>
        ) : isLoading || !data ? (
          <LoadingState centered={true} />
        ) : (
          <div className="flex flex-col gap-6">
            {/* KPI row */}
            <div
              className="grid grid-cols-2 lg:grid-cols-4 gap-3"
              data-testid="retrieval-section"
            >
              <KpiCard
                label={t('monitoring.kpiTotal')}
                value={
                  data.retrieval.total > 0
                    ? formatCount(data.retrieval.total)
                    : '—'
                }
                color={'var(--color-accent)'}
                spark={SPARK_TOTAL}
                hasData={data.retrieval.total > 0}
                sparkId="kpi-total"
              />
              <KpiCard
                label={t('monitoring.kpiAvgHit')}
                value="—"
                color={STATUS_COLORS.blue}
                spark={SPARK_HIT}
                hasData={false}
                sparkId="kpi-hit"
              />
              <KpiCard
                label={t('monitoring.kpiAvgLatency')}
                value={formatMs(data.retrieval.latency_p50_ms)}
                color={STATUS_COLORS.green}
                spark={SPARK_LAT}
                hasData={data.retrieval.latency_p50_ms != null}
                sparkId="kpi-lat"
              />
              <KpiCard
                label={t('monitoring.kpiGoodRate')}
                value={formatPct(data.feedback.good_ratio)}
                color={STATUS_COLORS.amber}
                spark={SPARK_RATE}
                hasData={data.feedback.good_ratio != null}
                sparkId="kpi-rate"
              />
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <ChartCard
                title={t('monitoring.chartQualityTitle')}
                label={t('monitoring.chartQualityLabel')}
                color={'var(--color-accent)'}
                values={SPARK_HIT}
                chartId="chart-quality"
              />
              <ChartCard
                title={t('monitoring.chartLatencyTitle')}
                label={t('monitoring.chartLatencyLabel')}
                color={STATUS_COLORS.green}
                values={SPARK_LAT}
                chartId="chart-latency"
                invert
              />
            </div>

            {/* Feedback + Alerts */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              <div
                className="lg:col-span-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-5"
                data-testid="feedback-section"
              >
                <h2 className="flex items-center gap-2 m-0 mb-4 text-sm font-medium text-[var(--color-text-primary)]">
                  <MessageSquare
                    size={16}
                    className="text-[var(--color-accent)]"
                  />
                  {t('monitoring.feedbackSectionTitle')}
                </h2>
                {data.feedback.total === 0 ? (
                  <EmptyState
                    icon={<ThumbsUp size={24} />}
                    title={t('monitoring.feedbackEmptyTitle')}
                    description={t('monitoring.feedbackEmptyDesc')}
                    centered
                  />
                ) : (
                  <>
                    <div className="grid grid-cols-3 gap-3 mb-4">
                      <StatBox
                        label={t('monitoring.feedback.good')}
                        value={formatCount(data.feedback.good_count)}
                        color={STATUS_COLORS.green}
                      />
                      <StatBox
                        label={t('monitoring.feedback.bad')}
                        value={formatCount(data.feedback.bad_count)}
                        color={STATUS_COLORS.red}
                      />
                      <StatBox
                        label={t('monitoring.feedback.unrated')}
                        value={formatCount(
                          Math.max(
                            data.feedback.total -
                              data.feedback.good_count -
                              data.feedback.bad_count,
                            0,
                          ),
                        )}
                        color="var(--color-text-muted)"
                      />
                    </div>
                    <div className="font-mono text-[11px] text-[var(--color-text-muted)]">
                      {t('monitoring.feedback.title')}{' '}
                      {formatPct(data.feedback.good_ratio)}
                    </div>
                  </>
                )}
              </div>

              <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-5">
                <h2 className="flex items-center gap-2 m-0 mb-4 text-sm font-medium text-[var(--color-text-primary)]">
                  <AlertTriangle
                    size={16}
                    className="text-[var(--color-warning, #d97706)]"
                  />
                  {t('monitoring.alertsSectionTitle')}
                </h2>
                {data.alerts.length === 0 ? (
                  <div
                    className="flex items-center gap-2 px-3 py-2.5 rounded-lg"
                    style={{
                      borderColor: withAlpha(STATUS_COLORS.green, 0.18),
                      backgroundColor: withAlpha(STATUS_COLORS.green, 0.06),
                      borderWidth: 1,
                      borderStyle: 'solid',
                    }}
                  >
                    <CheckCircle2
                      size={16}
                      className="text-[var(--color-accent)]"
                    />
                    <span className="text-xs text-[var(--color-text-secondary)]">
                      {t('monitoring.alerts.none')}
                    </span>
                  </div>
                ) : (
                  <ul
                    className="flex flex-col gap-2"
                    data-testid="alerts-section"
                  >
                    {data.alerts.map((alert) => (
                      <li
                        key={alert.code}
                        className="flex items-center justify-between px-3 py-2 rounded-lg bg-[var(--color-surface-elevated)] border border-[var(--color-border)]"
                        data-testid={`alert-${alert.code}`}
                      >
                        <span className="text-xs text-[var(--color-text-secondary)]">
                          {t(`monitoring.alerts.${alert.code}`, {
                            current: formatAlertValue(
                              alert.code,
                              alert.current,
                            ),
                            threshold: formatAlertValue(
                              alert.code,
                              alert.threshold,
                            ),
                          })}
                        </span>
                        <span
                          className="inline-block w-2 h-2 rounded-full"
                          style={{
                            background: statusColor(alert.level),
                            boxShadow: `0 0 5px ${statusColor(alert.level)}80`,
                          }}
                        />
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatBox({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="text-center px-2 py-3 rounded-lg bg-[var(--color-surface-elevated)] border border-[var(--color-border)]">
      <div className="text-xl font-bold mb-1" style={{ color }}>
        {value}
      </div>
      <div className="font-mono text-[11px] text-[var(--color-text-muted)]">
        {label}
      </div>
    </div>
  );
}
