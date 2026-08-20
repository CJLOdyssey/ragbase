import { History, Pencil, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { PromptItem } from '../../api/client/prompts';
import { MonoBadge, StatusBadge, Tag } from './PromptBadges';

interface Props {
  prompts: PromptItem[];
  onEdit: (row: PromptItem) => void;
  onDelete: (row: PromptItem) => void;
  onHistory: (row: PromptItem) => void;
  onSelect: (row: PromptItem) => void;
}

const GRID = '2fr 3.5fr 80px 110px 90px 110px';

const HEADERS = [
  'prompts.table.name',
  'prompts.table.desc',
  'prompts.table.status',
  'prompts.table.version',
  'prompts.table.uses',
  'prompts.table.actions',
] as const;

export default function PromptTable({
  prompts,
  onEdit,
  onDelete,
  onHistory,
  onSelect,
}: Props) {
  const { t } = useTranslation();
  return (
    <div className="rounded-[14px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] overflow-hidden">
      <div
        className="grid items-center h-10 px-[18px] border-b border-[var(--color-border-subtle)] bg-[color-mix(in_srgb,var(--color-surface-hover)_40%,transparent)]"
        style={{ gridTemplateColumns: GRID }}
      >
        {HEADERS.map((k) => (
          <div
            key={k}
            className="text-[10.5px] font-semibold tracking-[0.07em] uppercase font-mono text-[var(--color-text-tertiary)]"
          >
            {t(k)}
          </div>
        ))}
      </div>

      {prompts.map((row) => (
        <div
          key={row.id}
          onClick={() => onSelect(row)}
          className="grid items-center h-[60px] px-[18px] border-b border-[var(--color-border-subtle)] hover:bg-[color-mix(in_srgb,var(--color-accent)_4%,transparent)] transition-colors cursor-pointer"
          style={{ gridTemplateColumns: GRID }}
        >
          <div className="min-w-0 pr-3">
            <div
              className="text-[13.5px] font-medium text-[var(--color-text-primary)] mb-0.5 truncate"
              title={row.name}
            >
              {row.name}
            </div>
            <div className="flex gap-1 flex-wrap">
              {(row as unknown as { tags?: string[] }).tags ? (
                ((row as unknown as { tags: string[] }).tags as string[]).map(
                  (tag) => <Tag key={tag}>{tag}</Tag>,
                )
              ) : (
                <Tag>{row.category}</Tag>
              )}
            </div>
          </div>

          <div
            className="text-[12.5px] text-[var(--color-text-secondary)] truncate pr-3"
            title={row.description || ''}
          >
            {row.description || '—'}
          </div>

          <div>
            <StatusBadge status={row.status} />
          </div>

          <div>
            <MonoBadge>{row.version}</MonoBadge>
          </div>

          <div className="text-[12.5px] font-mono text-[var(--color-text-secondary)]">
            {((row as unknown as { uses?: number }).uses ?? 0).toLocaleString()}
          </div>

          <div
            className="flex gap-1 justify-end"
            onClick={(e) => e.stopPropagation()}
          >
            <ActionButton
              title={t('prompts.list.edit')}
              onClick={() => onEdit(row)}
              hoverVar="--color-accent"
            >
              <Pencil size={12} />
            </ActionButton>
            <ActionButton
              title={t('prompts.list.history')}
              onClick={() => onHistory(row)}
              hoverVar="--color-accent-soft"
            >
              <History size={12} />
            </ActionButton>
            <ActionButton
              title={t('prompts.list.delete')}
              onClick={() => onDelete(row)}
              hoverVar="--color-danger"
            >
              <Trash2 size={12} />
            </ActionButton>
          </div>
        </div>
      ))}
    </div>
  );
}

function ActionButton({
  title,
  hoverVar,
  onClick,
  children,
}: {
  title: string;
  hoverVar: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      title={title}
      aria-label={title}
      onClick={onClick}
      className="w-[27px] h-[27px] rounded-md border bg-[var(--color-surface)] text-[var(--color-text-muted)] cursor-pointer inline-flex items-center justify-center transition-colors border-[var(--color-border)] hover:bg-[color-mix(in_srgb,var(--hover)_12%,transparent)] hover:text-[var(--hover)] hover:border-[color-mix(in_srgb,var(--hover)_30%,transparent)]"
      style={{ ['--hover' as string]: `var(${hoverVar})` }}
    >
      {children}
    </button>
  );
}
