import { useTranslation } from 'react-i18next';
import type { PromptTab } from './usePromptLibrary';

interface Props {
  tab: PromptTab;
  onChange: (t: PromptTab) => void;
  counts: { all: number; published: number; draft: number };
}

const TAB_CONFIG: Array<{ key: PromptTab; i18nKey: string }> = [
  { key: 'all', i18nKey: 'prompts.tabAll' },
  { key: 'published', i18nKey: 'prompts.statusEnabled' },
  { key: 'draft', i18nKey: 'prompts.statusDraft' },
];

export default function PromptTabs({ tab, onChange, counts }: Props) {
  const { t } = useTranslation();
  return (
    <div className="flex gap-1.5 mb-5">
      {TAB_CONFIG.map(({ key, i18nKey }) => {
        const active = tab === key;
        const count = counts[key];
        return (
          <button
            key={key}
            onClick={() => onChange(key)}
            className={`px-[13px] py-[5px] rounded-lg text-[12.5px] font-sans cursor-pointer inline-flex items-center gap-1.5 transition-colors border ${active ? 'bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)] text-[var(--color-accent-muted)] border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)] font-medium' : 'bg-transparent text-[var(--color-text-muted)] border-[var(--color-border)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]'}`}
          >
            {t(i18nKey)}
            <span
              className={`text-[10.5px] font-mono rounded px-[5px] py-px ${active ? 'bg-[color-mix(in_srgb,var(--color-accent)_20%,transparent)] text-[var(--color-accent-soft)]' : 'bg-[var(--color-surface-hover)] text-[var(--color-text-tertiary)]'}`}
            >
              {count}
            </span>
          </button>
        );
      })}
    </div>
  );
}
