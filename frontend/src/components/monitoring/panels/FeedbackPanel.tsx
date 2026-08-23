import { useTranslation } from 'react-i18next';
import { MessageSquare, ThumbsUp } from 'lucide-react';
import { STATUS_COLORS } from '../../shared/statusColors';
import type { TimeRangeQuery } from '../../../types/monitoring';
import EmptyState from '../../shared/EmptyState';
import BadFeedbackPanel from '../BadFeedbackPanel';
import DataGate from '../DataGate';
import { formatCount, formatPct } from '../formatters';
import { useMonitoringSummaryQuery } from '../useMonitoringQueries';

interface Props {
  timeQuery: TimeRangeQuery;
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

/** 差评审查 Tab：反馈闭环工作台——用户反馈统计 + 差评人工分诊队列。 */
export default function FeedbackPanel({ timeQuery }: Props) {
  const { t } = useTranslation();
  const { data, isLoading, isError, refetch } =
    useMonitoringSummaryQuery(timeQuery);

  return (
    <DataGate
      loading={isLoading}
      error={isError}
      ready={data != null}
      onRetry={() => void refetch()}
    >
      {data ? (
        <div className="flex flex-col gap-3">
          <div
            className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-5"
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

          <BadFeedbackPanel timeQuery={timeQuery} />
        </div>
      ) : null}
    </DataGate>
  );
}
