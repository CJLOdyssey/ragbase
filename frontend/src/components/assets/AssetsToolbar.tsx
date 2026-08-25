import { Search } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  FORMAT_OPTIONS,
  STATUS_OPTIONS,
  TIME_RANGES,
  type TimeRange,
} from './assetUtils';

export interface KbOption {
  id: string;
  name: string;
}

export interface AssetsToolbarProps {
  search: string;
  onSearch: (v: string) => void;
  formats: string[];
  onFormatsChange: (v: string[]) => void;
  statuses: string[];
  onStatusesChange: (v: string[]) => void;
  kbFilter: string;
  onKbFilterChange: (v: string) => void;
  kbs: KbOption[];
  timeRange: TimeRange;
  onTimeRangeChange: (v: TimeRange) => void;
  customFrom: string;
  customTo: string;
  onCustomTimeChange: (from: string, to: string) => void;
}

export default function AssetsToolbar({
  search,
  onSearch,
  formats,
  onFormatsChange,
  statuses,
  onStatusesChange,
  kbFilter,
  onKbFilterChange,
  kbs,
  timeRange,
  onTimeRangeChange,
  customFrom,
  customTo,
  onCustomTimeChange,
}: AssetsToolbarProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-3">
      {/* 搜索行：仅搜索框（居中） */}
      <div className="flex items-center justify-center gap-2">
        <div className="relative w-full max-w-[360px]">
          <Search
            size={14}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)] pointer-events-none"
          />
          <input
            value={search}
            onChange={(e) => onSearch(e.target.value)}
            placeholder={t('assets.toolbar.searchPlaceholder', {
              defaultValue: '请输入文件名',
            })}
            aria-label={t('assets.toolbar.searchPlaceholder', {
              defaultValue: '请输入文件名',
            })}
            className="w-full h-9 pl-8 pr-3 rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] text-sm outline-none focus:border-[var(--color-accent)]"
            data-testid="assets-search"
          />
        </div>
      </div>

      {/* 筛选行：四下拉并列（居中） */}
      <div className="flex flex-wrap items-center justify-center gap-3">
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-mono tracking-[0.06em] uppercase text-[var(--color-text-tertiary)]">
            {t('assets.filter.kb', { defaultValue: '知识库' })}
          </span>
          <select
            value={kbFilter}
            onChange={(e) => onKbFilterChange(e.target.value)}
            className="h-8 w-[130px] rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-2 text-sm text-[var(--color-text-secondary)] outline-none focus:border-[var(--color-accent)]"
            data-testid="filter-kb"
          >
            <option value="all">
              {t('common.all', { defaultValue: '全部' })}
            </option>
            <option value="unassigned">
              {t('assets.filter.unassigned', { defaultValue: '未分配' })}
            </option>
            {kbs.map((kb) => (
              <option key={kb.id} value={kb.id}>
                {kb.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-mono tracking-[0.06em] uppercase text-[var(--color-text-tertiary)]">
            {t('assets.filter.format', { defaultValue: '格式' })}
          </span>
          <select
            value={formats.length === 0 ? 'all' : formats[0]}
            onChange={(e) => {
              const v = e.target.value;
              if (v === 'all') onFormatsChange([]);
              else onFormatsChange([v]);
            }}
            className="h-8 w-[110px] rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-2 text-sm text-[var(--color-text-secondary)] outline-none focus:border-[var(--color-accent)]"
            data-testid="filter-format"
          >
            <option value="all">
              {t('common.all', { defaultValue: '全部' })}
            </option>
            {FORMAT_OPTIONS.map((fmt) => (
              <option key={fmt} value={fmt}>
                {fmt.toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-mono tracking-[0.06em] uppercase text-[var(--color-text-tertiary)]">
            {t('assets.filter.status', { defaultValue: '索引状态' })}
          </span>
          <select
            value={statuses.length === 0 ? 'all' : statuses[0]}
            onChange={(e) => {
              const v = e.target.value;
              if (v === 'all') onStatusesChange([]);
              else onStatusesChange([v]);
            }}
            className="h-8 w-[110px] rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-2 text-sm text-[var(--color-text-secondary)] outline-none focus:border-[var(--color-accent)]"
            data-testid="filter-status"
          >
            <option value="all">
              {t('common.all', { defaultValue: '全部' })}
            </option>
            {STATUS_OPTIONS.map((s) => {
              const label = t(`assets.status.${s}`, { defaultValue: s });
              return (
                <option key={s} value={s}>
                  {label}
                </option>
              );
            })}
          </select>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-mono tracking-[0.06em] uppercase text-[var(--color-text-tertiary)]">
            {t('assets.filter.time', { defaultValue: '更新时间' })}
          </span>
          <select
            value={timeRange}
            onChange={(e) => onTimeRangeChange(e.target.value as TimeRange)}
            className="h-8 w-[110px] rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-2 text-sm text-[var(--color-text-secondary)] outline-none focus:border-[var(--color-accent)]"
            data-testid="filter-time"
          >
            {TIME_RANGES.map((r) => (
              <option key={r.value} value={r.value}>
                {t(r.labelKey, { defaultValue: r.defaultLabel })}
              </option>
            ))}
          </select>
          {timeRange === 'custom' && (
            <span className="flex items-center gap-1 ml-1">
              <input
                type="date"
                value={customFrom}
                onChange={(e) => onCustomTimeChange(e.target.value, customTo)}
                className="h-8 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-2 text-xs"
                data-testid="filter-time-from"
              />
              <span className="text-[var(--color-text-tertiary)]">~</span>
              <input
                type="date"
                value={customTo}
                onChange={(e) => onCustomTimeChange(customFrom, e.target.value)}
                className="h-8 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-2 text-xs"
                data-testid="filter-time-to"
              />
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
