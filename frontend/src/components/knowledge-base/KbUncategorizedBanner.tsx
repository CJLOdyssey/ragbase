import { ArrowRight, FileWarning } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

interface KbUncategorizedBannerProps {
  count: number;
}

/** 知识库页顶部的未分类提醒 — 只报数量并引导到素材页处理，
 *  不再内联资产管理（职责归位：分配/索引导线在素材页闭环）。 */
export default function KbUncategorizedBanner({
  count,
}: KbUncategorizedBannerProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  if (count <= 0) return null;

  return (
    <button
      type="button"
      onClick={() => navigate('/assets')}
      data-testid="kb-uncategorized-banner"
      className="group flex w-full cursor-pointer items-center gap-2.5 rounded-lg border border-[color-mix(in_srgb,var(--color-warning)_35%,transparent)] bg-[color-mix(in_srgb,var(--color-warning)_7%,transparent)] px-4 py-2.5 text-left transition-colors hover:bg-[color-mix(in_srgb,var(--color-warning)_12%,transparent)]"
    >
      <FileWarning
        size={15}
        className="shrink-0"
        style={{ color: 'var(--color-warning)' }}
      />
      <span className="text-sm text-[var(--color-text-secondary)]">
        {t('kb.uncategorizedBanner', { count })}
      </span>
      <span className="ml-auto inline-flex shrink-0 items-center gap-1 text-xs font-medium text-[var(--color-accent)]">
        {t('kb.goHandle')}
        <ArrowRight
          size={13}
          className="transition-transform group-hover:translate-x-0.5"
        />
      </span>
    </button>
  );
}
