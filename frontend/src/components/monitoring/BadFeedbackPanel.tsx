import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCheck, MessageSquareWarning, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  fetchBadFeedback,
  reviewBadFeedback,
} from '../../api/client/monitoring';
import type {
  BadFeedbackItem,
  ReviewRootCause,
  ReviewStatus,
  TimeRangeQuery,
} from '../../types/monitoring';
import EmptyState from '../shared/EmptyState';

const CAUSES: Array<{ value: ReviewRootCause; key: string }> = [
  { value: 'retrieval_miss', key: 'causeRetrievalMiss' },
  { value: 'wrong_answer', key: 'causeWrongAnswer' },
  { value: 'bad_format', key: 'causeBadFormat' },
  { value: 'other', key: 'causeOther' },
];

const STATUS_FILTERS: Array<{ value: ReviewStatus | 'all'; key: string }> = [
  { value: 'pending', key: 'statusPending' },
  { value: 'resolved', key: 'statusResolved' },
  { value: 'dismissed', key: 'statusDismissed' },
  { value: 'all', key: 'filterAll' },
];

/**
 * 差评审查队列 —— 在线反馈闭环的人工分诊入口。
 * 每条差评可标注根因并流转状态；根因枚举即未来黄金评测集的类别体系。
 */
export default function BadFeedbackPanel({
  timeQuery,
}: {
  timeQuery: TimeRangeQuery;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | 'all'>(
    'pending',
  );
  const rangeKey = timeQuery.since
    ? `${timeQuery.since}-${timeQuery.until}`
    : timeQuery.window_hours;

  const { data, isLoading } = useQuery({
    queryKey: ['bad-feedback', rangeKey, statusFilter],
    queryFn: () =>
      fetchBadFeedback({
        window_hours: timeQuery.window_hours,
        since: timeQuery.since,
        until: timeQuery.until,
        status: statusFilter === 'all' ? undefined : statusFilter,
        page_size: 50,
      }),
  });

  const reviewMutation = useMutation({
    mutationFn: ({
      feedbackId,
      status,
      rootCause,
    }: {
      feedbackId: string;
      status: ReviewStatus;
      rootCause?: ReviewRootCause;
    }) => reviewBadFeedback(feedbackId, { status, root_cause: rootCause }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['bad-feedback'] }),
  });

  const items = data?.items ?? [];
  // 行内草稿态：每行独立的根因选择，避免互相干扰。
  const [drafts, setDrafts] = useState<Record<string, ReviewRootCause>>({});
  const draftMap = drafts;
  const setDraft = (id: string, cause: ReviewRootCause) =>
    setDrafts((prev) => ({ ...prev, [id]: cause }));

  const resolve = (item: BadFeedbackItem) => {
    const existing = item.review?.root_cause;
    reviewMutation.mutate({
      feedbackId: item.feedback_id,
      status: 'resolved',
      rootCause: draftMap[item.feedback_id] ?? existing ?? 'other',
    });
  };
  const dismiss = (item: BadFeedbackItem) =>
    reviewMutation.mutate({ feedbackId: item.feedback_id, status: 'dismissed' });

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 m-0 text-sm font-medium text-[var(--color-text-primary)]">
          <MessageSquareWarning
            size={16}
            className="text-[var(--color-warning, #f59e0b)]"
          />
          {t('monitoring.review.title')}
          {(data?.total ?? 0) > 0 && (
            <span className="font-mono text-[11px] text-[var(--color-text-muted)]">
              ({data?.total})
            </span>
          )}
        </h2>
        <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] p-0.5">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => setStatusFilter(s.value)}
              className={`px-2 py-1 rounded-md text-xs cursor-pointer border-none transition-colors duration-150 ${
                statusFilter === s.value
                  ? 'bg-[var(--color-surface-hover)] text-[var(--color-text-primary)]'
                  : 'bg-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              }`}
            >
              {t(`monitoring.review.${s.key}`)}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="py-6 text-center text-xs text-[var(--color-text-muted)]">
          …
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={<MessageSquareWarning size={22} />}
          title={t('monitoring.review.empty')}
          centered
        />
      ) : (
        <ul className="flex flex-col gap-2 m-0 p-0 list-none" data-testid="review-list">
          {items.map((item) => {
            const st = item.review?.status ?? 'pending';
            const resolved = st === 'resolved';
            const dismissed = st === 'dismissed';
            return (
              <li
                key={item.feedback_id}
                className={`rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-3 py-2.5 ${
                  dismissed ? 'opacity-50' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-3 mb-1.5">
                  <span className="text-xs text-[var(--color-text-secondary)] line-clamp-1">
                    {item.query || '—'}
                  </span>
                  <span className="shrink-0 font-mono text-[10px] text-[var(--color-text-muted)]">
                    {item.created_at
                      ? new Date(item.created_at).toLocaleDateString('zh-CN')
                      : ''}
                  </span>
                </div>
                {item.answer && (
                  <p className="m-0 mb-2 text-[11px] leading-relaxed text-[var(--color-text-muted)] line-clamp-2">
                    {item.answer}
                  </p>
                )}
                <div className="flex flex-wrap items-center gap-1.5">
                  <select
                    value={
                      draftMap[item.feedback_id] ??
                      item.review?.root_cause ??
                      ''
                    }
                    onChange={(e) =>
                      setDraft(
                        item.feedback_id,
                        e.target.value as ReviewRootCause,
                      )
                    }
                    disabled={dismissed}
                    className="h-7 px-1.5 rounded-md border border-[var(--color-border)] bg-transparent text-[11px] text-[var(--color-text-secondary)] cursor-pointer disabled:opacity-50"
                  >
                    <option value="" disabled>
                      {t('monitoring.review.selectCause')}
                    </option>
                    {CAUSES.map((c) => (
                      <option key={c.value} value={c.value}>
                        {t(`monitoring.review.${c.key}`)}
                      </option>
                    ))}
                  </select>
                  {!dismissed && (
                    <>
                      <button
                        type="button"
                        onClick={() => resolve(item)}
                        className="inline-flex items-center gap-1 h-7 px-2 rounded-md border border-[var(--color-border)] bg-transparent text-[11px] text-[var(--color-success)] cursor-pointer hover:bg-[var(--color-surface-hover)]"
                      >
                        <CheckCheck size={11} />
                        {t('monitoring.review.resolve')}
                      </button>
                      <button
                        type="button"
                        onClick={() => dismiss(item)}
                        className="inline-flex items-center gap-1 h-7 px-2 rounded-md border-none bg-transparent text-[11px] text-[var(--color-text-muted)] cursor-pointer hover:text-[var(--color-text-secondary)]"
                      >
                        <X size={11} />
                        {t('monitoring.review.dismiss')}
                      </button>
                    </>
                  )}
                  {st !== 'pending' && (
                    <span
                      className={`ml-auto font-mono text-[10px] ${
                        resolved
                          ? 'text-[var(--color-success)]'
                          : 'text-[var(--color-text-muted)]'
                      }`}
                    >
                      {t(
                        `monitoring.review.${
                          resolved ? 'statusResolved' : 'statusDismissed'
                        }`,
                      )}
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
