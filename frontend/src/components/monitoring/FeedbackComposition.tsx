import { useMemo } from 'react';
import EChart, { type EChartsOption } from '../shared/EChart';
import EmptyState from '../shared/EmptyState';
import { useTranslation } from 'react-i18next';
import type { MonitoringPoint } from '../../types/monitoring';
import { feedbackCompositionOption } from './chartOptions';

interface Props {
  points: MonitoringPoint[];
  intraday: boolean;
}

/** 反馈构成趋势：百分比堆叠柱（好评/差评/未评价）。 */
export default function FeedbackComposition({ points, intraday }: Props) {
  const { t } = useTranslation();
  const hasData = points.some((p) => p.retrievals > 0);

  const option: EChartsOption = useMemo(
    () =>
      feedbackCompositionOption({
        points,
        labels: {
          good: t('monitoring.feedback.good'),
          bad: t('monitoring.feedback.bad'),
          unrated: t('monitoring.feedback.unrated'),
        },
        intraday,
      }),
    [points, intraday, t],
  );

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-5">
      <h3 className="m-0 mb-2 text-sm font-medium text-[var(--color-text-primary)]">
        {t('monitoring.chartCompositionTitle')}
      </h3>
      {!hasData ? (
        <EmptyState
          title={t('monitoring.noData')}
          description={t('monitoring.chartCompositionDesc')}
          centered
        />
      ) : (
        <EChart
          option={option}
          height={240}
          ariaLabel={t('monitoring.chartCompositionTitle')}
          testId="chart-composition"
        />
      )}
    </div>
  );
}
