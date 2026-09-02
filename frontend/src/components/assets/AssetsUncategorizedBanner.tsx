import { ArrowRight, FileWarning } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface AssetsUncategorizedBannerProps {
  count: number;
  onHandle: () => void;
}

/** 一行式未分类提醒 — 无论多少未分类素材，顶部永远只占一行。
 *  点击进入主表格「未分类」筛选态，处理动作全部复用既有行内交互。 */
export default function AssetsUncategorizedBanner({
  count,
  onHandle,
}: AssetsUncategorizedBannerProps) {
  const { t } = useTranslation();
  if (count <= 0) return null;

  return (
    <button
      type="button"
      onClick={onHandle}
      data-testid="assets-uncategorized-banner"
      className="group flex w-full cursor-pointer items-center gap-2.5 rounded-lg border border-[color-mix(in_srgb,var(--color-warning)_35%,transparent)] bg-[color-mix(in_srgb,var(--color-warning)_7%,transparent)] px-4 py-2.5 text-left transition-colors hover:bg-[color-mix(in_srgb,var(--color-warning)_12%,transparent)]"
    >
      <FileWarning
        size={15}
        className="shrink-0"
        style={{ color: 'var(--color-warning)' }}
      />
      <span className="text-sm text-[var(--color-text-secondary)]">
        {t('assets.uncategorized.banner', { count })}
      </span>
      <span className="ml-auto inline-flex shrink-0 items-center gap-1 text-xs font-medium text-[var(--color-accent)]">
        {t('assets.uncategorized.handle')}
        <ArrowRight
          size={13}
          className="transition-transform group-hover:translate-x-0.5"
        />
      </span>
    </button>
  );
}
