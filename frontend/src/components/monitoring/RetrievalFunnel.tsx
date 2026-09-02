import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import type { MonitoringSummary } from '../../types/monitoring';
import EmptyState from '../shared/EmptyState';
import EChart, { type EChartsOption } from '../shared/EChart';
import { retrievalFunnelOption, type FunnelStage } from './chartOptions';

interface Props {
  summary: MonitoringSummary;
}

/**
 * 检索转化漏斗：总检索 → 有命中 → 已评价 → 好评。
 * 每一级收窄即该环节漏损（语料缺口 / 覆盖率不足 / 答案质量差）。
 */
export default function RetrievalFunnel({ summary }: Props) {
  const { t } = useTranslation();
  const { retrieval, feedback } = summary;

  const stages: FunnelStage[] = useMemo(
    () => [
      { name: t('monitoring.funnel.queries'), value: retrieval.total },
      {
        name: t('monitoring.funnel.hit'),
        value: Math.max(retrieval.total - retrieval.empty_recall_count, 0),
      },
      { name: t('monitoring.funnel.rated'), value: feedback.total },
      { name: t('monitoring.funnel.good'), value: feedback.good_count },
    ],
    [t, retrieval, feedback],
  );

  const option: EChartsOption = useMemo(
    () => retrievalFunnelOption({ stages }),
    [stages],
  );

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-5">
      <h3 className="m-0 mb-2 text-sm font-medium text-[var(--color-text-primary)]">
        {t('monitoring.funnel.title')}
      </h3>
      {retrieval.total === 0 ? (
        <EmptyState
          title={t('monitoring.noData')}
          description={t('monitoring.funnel.emptyDesc')}
          centered
        />
      ) : (
        <EChart
          option={option}
          height={280}
          ariaLabel={t('monitoring.funnel.title')}
          testId="chart-funnel"
        />
      )}
    </div>
  );
}
