import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface KbFilterChipProps {
  /** 'unassigned' 或知识库 id */
  kbFilter: string;
  /** 知识库名称（kbFilter 为具体 id 时展示） */
  kbName?: string;
  onClear: () => void;
}

/** 知识库筛选态 chip — 未分配显示「未分类」，具体库显示库名，点 × 清除。 */
export default function KbFilterChip({
  kbFilter,
  kbName,
  onClear,
}: KbFilterChipProps) {
  const { t } = useTranslation();
  const label =
    kbFilter === 'unassigned'
      ? t('assets.uncategorized.filterChip')
      : (kbName ?? kbFilter);
  return (
    <div>
      <span className="inline-flex items-center gap-1 rounded-full border border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)] bg-[color-mix(in_srgb,var(--color-accent)_10%,transparent)] py-0.5 pl-2.5 pr-1 text-xs font-medium text-[var(--color-accent-muted)]">
        {label}
        <button
          type="button"
          onClick={onClear}
          aria-label={t('assets.uncategorized.clearFilter')}
          data-testid="clear-kb-filter"
          className="flex h-4 w-4 cursor-pointer items-center justify-center rounded-full border-none bg-transparent p-0 text-[var(--color-accent-muted)] transition-colors hover:bg-[color-mix(in_srgb,var(--color-accent)_20%,transparent)] hover:text-[var(--color-accent)]"
        >
          <X size={11} />
        </button>
      </span>
    </div>
  );
}
