import { useState } from 'react';
import EmptyState from '../shared/EmptyState';
import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Search,
  ThumbsUp,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { fetchMonitoringSummary } from '../../api/client/monitoring';

const WINDOWS = [
  { hours: 24, key: 'monitoring.windowDay' },
  { hours: 24 * 7, key: 'monitoring.windowWeek' },
] as const;

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

function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="flex flex-col gap-1 px-4 py-3 rounded-lg bg-[var(--color-surface-raised)]">
      <span className="text-xs text-[var(--color-text-muted)]">{label}</span>
      <span className="text-lg font-semibold text-[var(--color-text-primary)]">
        {value}
      </span>
      {hint && (
        <span className="text-xs text-[var(--color-text-muted)]">{hint}</span>
      )}
    </div>
  );
}

export default function QualityMonitor() {
  const { t } = useTranslation();
  const [windowHours, setWindowHours] = useState(24);

  const { data, isLoading } = useQuery({
    queryKey: ['monitoring', windowHours],
    queryFn: () => fetchMonitoringSummary(windowHours),
  });

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)]">
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)] m-0">
          {t('monitoring.title')}
        </h1>
        <div className="flex items-center gap-1">
          {WINDOWS.map((w) => (
            <button
              key={w.hours}
              className={`px-3 py-1.5 rounded-md text-sm cursor-pointer border-none transition-colors duration-150 ${
                windowHours === w.hours
                  ? 'bg-[var(--color-accent)] text-white'
                  : 'bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
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
        {isLoading || !data ? (
          <p className="text-sm text-[var(--color-text-muted)]">
            {t('monitoring.loading')}
          </p>
        ) : (
          <div className="flex flex-col gap-6">
            <section
              className="flex flex-col gap-3"
              data-testid="retrieval-section"
            >
              <h2 className="flex items-center gap-2 text-sm font-medium text-[var(--color-text-secondary)] m-0">
                <Search size={16} />
                {t('monitoring.retrieval.title')}
              </h2>
              {data.retrieval.total === 0 ? (
                <EmptyState
                  icon={<BarChart3 size={24} />}
                  description={t('monitoring.retrieval.noSamples')}
                />
              ) : (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <StatCard
                    label={t('monitoring.retrieval.requests')}
                    value={formatCount(data.retrieval.total)}
                  />
                  <StatCard
                    label={t('monitoring.retrieval.emptyRecall')}
                    value={formatPct(data.retrieval.empty_recall_rate)}
                    hint={`${formatCount(data.retrieval.empty_recall_count)} / ${formatCount(data.retrieval.total)}`}
                  />
                  <StatCard
                    label={t('monitoring.retrieval.p50')}
                    value={formatMs(data.retrieval.latency_p50_ms)}
                  />
                  <StatCard
                    label={t('monitoring.retrieval.p95')}
                    value={formatMs(data.retrieval.latency_p95_ms)}
                  />
                </div>
              )}
            </section>

            <section
              className="flex flex-col gap-3"
              data-testid="feedback-section"
            >
              <h2 className="flex items-center gap-2 text-sm font-medium text-[var(--color-text-secondary)] m-0">
                <ThumbsUp size={16} />
                {t('monitoring.feedback.title')}
              </h2>
              {data.feedback.total === 0 ? (
                <EmptyState
                  icon={<ThumbsUp size={24} />}
                  description={t('monitoring.feedback.noSamples')}
                />
              ) : (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <StatCard
                    label={t('monitoring.feedback.title')}
                    value={formatPct(data.feedback.good_ratio)}
                  />
                  <StatCard
                    label={t('monitoring.feedback.good')}
                    value={formatCount(data.feedback.good_count)}
                  />
                  <StatCard
                    label={t('monitoring.feedback.bad')}
                    value={formatCount(data.feedback.bad_count)}
                  />
                </div>
              )}
            </section>

            <section
              className="flex flex-col gap-3"
              data-testid="alerts-section"
            >
              <h2 className="flex items-center gap-2 text-sm font-medium text-[var(--color-text-secondary)] m-0">
                <AlertTriangle size={16} />
                {t('monitoring.alerts.title')}
              </h2>
              {data.alerts.length === 0 ? (
                <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-[var(--color-surface-raised)]">
                  <CheckCircle2
                    size={16}
                    className="text-[var(--color-accent)]"
                  />
                  <span className="text-sm text-[var(--color-text-secondary)]">
                    {t('monitoring.alerts.none')}
                  </span>
                </div>
              ) : (
                <ul className="flex flex-col gap-2">
                  {data.alerts.map((alert) => (
                    <li
                      key={alert.code}
                      className="flex items-center gap-2 px-4 py-3 rounded-lg bg-[var(--color-surface-raised)]"
                      data-testid={`alert-${alert.code}`}
                    >
                      <AlertTriangle
                        size={16}
                        className="text-[var(--color-warning, #d97706)] shrink-0"
                      />
                      <span className="text-sm text-[var(--color-text-primary)]">
                        {t(`monitoring.alerts.${alert.code}`, {
                          current: formatAlertValue(alert.code, alert.current),
                          threshold: formatAlertValue(
                            alert.code,
                            alert.threshold,
                          ),
                        })}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
