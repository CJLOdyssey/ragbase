import { STATUS_COLORS } from '../shared/statusColors';
import { Box, Database, Pencil, Search, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { KnowledgeBase } from '../../api/client/knowledgeBases';

export const KB_ACCENTS = [
  'var(--color-accent)',
  'var(--color-accent)',
  STATUS_COLORS.blue,
  STATUS_COLORS.green,
  STATUS_COLORS.cyan,
  STATUS_COLORS.amber,
];

export interface KbCardProps {
  kb: KnowledgeBase;
  accent: string;
  assetCount: number;
  indexedCount: number;
  indexRate: number;
  onTest: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export function formatKbDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`;
}

export default function KbCard({
  kb,
  accent,
  assetCount,
  indexedCount,
  indexRate,
  onTest,
  onEdit,
  onDelete,
}: KbCardProps) {
  const { t } = useTranslation();
  return (
    <div className="group flex flex-col overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_12px_32px_rgba(0,0,0,0.35)]">
      <div
        className="h-[3px] w-full"
        style={{
          background: `linear-gradient(90deg, ${accent}, color-mix(in_srgb, ${accent} 0%, transparent))`,
        }}
      />

      <div className="flex flex-1 flex-col p-4">
        <div className="mb-3 flex items-start gap-3">
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] border"
            style={{
              color: accent,
              background: `color-mix(in_srgb, ${accent} 12%, transparent)`,
              borderColor: `color-mix(in_srgb, ${accent} 25%, transparent)`,
            }}
          >
            <Database size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-[15px] font-semibold text-[var(--color-text-primary)]">
              {kb.name}
            </div>
            <div className="mt-0.5 line-clamp-1 text-xs text-[var(--color-text-secondary)]">
              {kb.description || t('kb.noDescription')}
            </div>
            <div className="mt-1 flex items-center gap-1 font-mono text-[10px] uppercase tracking-wide text-[var(--color-text-muted)]">
              <Box size={10} className="shrink-0" />
              <span className="truncate">
                {kb.embedModel || t('kb.autoModel')}
              </span>
            </div>
          </div>
        </div>

        <div className="mb-3 grid grid-cols-3 gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-2.5">
          <Stat label={t('kb.statAssets')} value={assetCount} />
          <Stat label={t('kb.statIndexed')} value={indexedCount} />
          <Stat
            label={t('kb.statIndexRate')}
            value={assetCount ? `${indexRate}%` : '—'}
          />
        </div>

        <div className="mb-3 font-mono text-[11px] text-[var(--color-text-muted)]">
          {t('kb.updatedAt')} {formatKbDate(kb.updatedAt)}
        </div>

        <div className="mt-auto flex flex-wrap gap-1.5 border-t border-[var(--color-border)] pt-3">
          <button
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
            onClick={onTest}
          >
            <Search size={12} />
            {t('ragTest.button')}
          </button>
          <button
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
            onClick={onEdit}
          >
            <Pencil size={12} />
            {t('kb.edit')}
          </button>
          <button
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-[var(--color-danger)] transition-colors hover:bg-[color-mix(in_srgb,var(--color-danger)_12%,transparent)]"
            onClick={onDelete}
          >
            <Trash2 size={12} />
            {t('confirm.delete')}
          </button>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="text-center">
      <div className="text-[15px] font-bold leading-none tracking-tight text-[var(--color-text-primary)]">
        {value}
      </div>
      <div className="mt-1 font-mono text-[10px] uppercase tracking-wide text-[var(--color-text-muted)]">
        {label}
      </div>
    </div>
  );
}
