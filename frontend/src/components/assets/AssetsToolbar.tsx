import { Search, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export interface AssetsToolbarProps {
  search: string;
  onSearch: (v: string) => void;
  timeFrom: string;
  timeTo: string;
  onTimeChange: (from: string, to: string) => void;
  formats: string[];
  onFormatsChange: (v: string[]) => void;
  statuses: string[];
  onStatusesChange: (v: string[]) => void;
  onClear: () => void;
}

const FORMAT_OPTIONS = [
  'pdf',
  'txt',
  'md',
  'docx',
  'xlsx',
  'csv',
  'png',
  'jpg',
  'webp',
] as const;
const STATUS_OPTIONS = ['indexed', 'processing', 'failed', 'pending'] as const;

function toggleValue(list: string[], value: string): string[] {
  return list.includes(value)
    ? list.filter((v) => v !== value)
    : [...list, value];
}

export default function AssetsToolbar({
  search,
  onSearch,
  timeFrom,
  timeTo,
  onTimeChange,
  formats,
  onFormatsChange,
  statuses,
  onStatusesChange,
  onClear,
}: AssetsToolbarProps) {
  const { t } = useTranslation();
  const hasActive =
    search.trim() !== '' ||
    timeFrom !== '' ||
    timeTo !== '' ||
    formats.length > 0 ||
    statuses.length > 0;

  return (
    <div className="flex flex-col gap-3 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[220px] max-w-[320px]">
          <Search
            size={14}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)] pointer-events-none"
          />
          <input
            value={search}
            onChange={(e) => onSearch(e.target.value)}
            placeholder={t('assets.toolbar.searchPlaceholder', {
              defaultValue: '搜索文件名…',
            })}
            aria-label={t('assets.toolbar.searchPlaceholder', {
              defaultValue: '搜索文件名',
            })}
            className="w-full h-9 pl-8 pr-8 rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] text-sm outline-none focus:border-[var(--color-accent)]"
            data-testid="assets-search"
          />
          {search && (
            <button
              type="button"
              aria-label="clear search"
              onClick={() => onSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-6 h-6 inline-flex items-center justify-center rounded text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)]"
            >
              <X size={12} />
            </button>
          )}
        </div>

        <input
          type="date"
          value={timeFrom}
          onChange={(e) => onTimeChange(e.target.value, timeTo)}
          aria-label={t('assets.toolbar.timeFrom', {
            defaultValue: '开始时间',
          })}
          className="h-9 rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-2 text-sm text-[var(--color-text-secondary)] outline-none focus:border-[var(--color-accent)]"
          data-testid="assets-time-from"
        />
        <span className="text-[var(--color-text-tertiary)]">~</span>
        <input
          type="date"
          value={timeTo}
          onChange={(e) => onTimeChange(timeFrom, e.target.value)}
          aria-label={t('assets.toolbar.timeTo', { defaultValue: '结束时间' })}
          className="h-9 rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-2 text-sm text-[var(--color-text-secondary)] outline-none focus:border-[var(--color-accent)]"
          data-testid="assets-time-to"
        />

        {hasActive && (
          <button
            type="button"
            onClick={onClear}
            className="h-9 px-3 rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]"
            data-testid="assets-clear"
          >
            {t('assets.toolbar.clear', { defaultValue: '清除' })}
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-mono tracking-[0.06em] uppercase text-[var(--color-text-tertiary)]">
          格式
        </span>
        <div className="flex flex-wrap gap-1.5">
          {FORMAT_OPTIONS.map((fmt) => {
            const active = formats.includes(fmt);
            return (
              <button
                key={fmt}
                type="button"
                onClick={() => onFormatsChange(toggleValue(formats, fmt))}
                aria-pressed={active}
                className={`px-2.5 py-1 rounded-full text-[11px] font-mono uppercase border transition-colors ${active ? 'bg-[var(--color-accent)] text-white border-[var(--color-accent)]' : 'bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] border-[var(--color-border)] hover:border-[var(--color-border-strong)]'}`}
                data-testid={`format-${fmt}`}
              >
                {fmt}
              </button>
            );
          })}
        </div>

        <span className="ml-3 text-[11px] font-mono tracking-[0.06em] uppercase text-[var(--color-text-tertiary)]">
          状态
        </span>
        <div className="flex flex-wrap gap-1.5">
          {STATUS_OPTIONS.map((s) => {
            const active = statuses.includes(s);
            return (
              <button
                key={s}
                type="button"
                onClick={() => onStatusesChange(toggleValue(statuses, s))}
                aria-pressed={active}
                className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors ${active ? 'bg-[var(--color-surface-hover)] text-[var(--color-text-primary)] border-[var(--color-border-strong)]' : 'bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] border-[var(--color-border)]'}`}
                data-testid={`status-${s}`}
              >
                {t(`assets.status.${s}`, { defaultValue: s })}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
