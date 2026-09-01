import { BookText, LayoutGrid, Plus, Search, Table2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { PromptView } from './usePromptLibrary';

interface Props {
  search: string;
  onSearchChange: (v: string) => void;
  view: PromptView;
  onViewChange: (v: PromptView) => void;
  onNew: () => void;
}

export default function PromptHeader({
  search,
  onSearchChange,
  view,
  onViewChange,
  onNew,
}: Props) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-3 px-4 py-4 border-b border-[var(--color-border)] shrink-0 sm:px-6 md:px-8">
      {/* Row 1: 标题 */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center border text-[var(--color-accent-soft)] bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)] border-[color-mix(in_srgb,var(--color-accent)_22%,transparent)] shrink-0">
          <BookText size={14} />
        </div>
        <div className="min-w-0">
          <h1 className="m-0 text-[18px] font-bold tracking-[-0.03em] text-[var(--color-text-primary)] leading-none">
            {t('prompts.title')}
          </h1>
          <p className="m-0 mt-1 text-[12.5px] leading-[1.4] text-[var(--color-text-muted)] hidden sm:block">
            {t('prompts.subtitle')}
          </p>
        </div>
      </div>

      {/* Row 2: 搜索 + 新建 + 视图切换 */}
      <div className="flex items-center justify-between gap-2">
        <div className="relative flex-1">
          <Search
            size={13}
            className="absolute left-[9px] top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)] pointer-events-none"
          />
          <input
            type="search"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={t('prompts.searchPlaceholder')}
            className="h-[34px] w-full pl-[30px] pr-3 rounded-lg border bg-[var(--color-surface)] text-[13px] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] outline-none border-[var(--color-border)] focus:border-[color-mix(in_srgb,var(--color-accent)_40%,transparent)] focus:shadow-[0_0_0_3px_color-mix(in_srgb,var(--color-accent)_8%,transparent)] transition-colors"
          />
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onNew}
            className="inline-flex items-center gap-1.5 min-h-[44px] px-3 sm:px-4 rounded-full border-none text-white text-[13px] font-medium cursor-pointer whitespace-nowrap bg-[linear-gradient(135deg,var(--color-accent),var(--color-accent-hover))] shadow-[0_2px_10px_color-mix(in_srgb,var(--color-accent)_28%,transparent)] hover:shadow-[0_4px_18px_color-mix(in_srgb,var(--color-accent)_45%,transparent)] hover:-translate-y-px transition-all"
          >
            <Plus size={14} />
            {t('prompts.editor.new')}
          </button>

          <div className="flex items-center p-0.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raised)]">
            {(['table', 'grid'] as const).map((v) => (
              <button
                key={v}
                onClick={() => onViewChange(v)}
                aria-label={v === 'table' ? '表格视图' : '卡片视图'}
                className={`min-w-[44px] min-h-[44px] rounded-md border-none cursor-pointer inline-flex items-center justify-center transition-colors ${view === v ? 'bg-[var(--color-surface-overlay)] text-[var(--color-text-primary)] shadow-sm' : 'bg-transparent text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]'}`}
              >
                {v === 'table' ? <Table2 size={14} /> : <LayoutGrid size={14} />}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
