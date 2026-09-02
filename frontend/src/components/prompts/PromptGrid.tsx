import { History, Pencil, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { PromptItem } from '../../api/client/prompts';
import { DataGrid } from '../shared/list';
import { ActionButton } from '../shared/list/badges';
import { MonoBadge, StatusBadge, Tag } from './PromptBadges';

interface Props {
  prompts: PromptItem[];
  onSelect: (id: string) => void;
  onEdit: (row: PromptItem) => void;
  onDelete: (row: PromptItem) => void;
  onHistory: (row: PromptItem) => void;
}

export default function PromptGrid({
  prompts,
  onSelect,
  onEdit,
  onDelete,
  onHistory,
}: Props) {
  const { t } = useTranslation();

  const renderCard = (p: PromptItem) => {
    return (
      <div
        key={p.id}
        onClick={() => onSelect(p.id)}
        data-testid={`prompt-item-${p.id}`}
        className="text-left bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[14px] p-[18px] pb-3.5 cursor-pointer transition-all hover:border-[var(--color-border-strong)] hover:-translate-y-0.5 hover:shadow-[0_8px_32px_rgba(0,0,0,0.25)]"
      >
        <div className="flex items-center justify-between mb-2.5">
          <span className="text-sm font-semibold text-[var(--color-text-primary)] truncate pr-2">
            {p.name}
          </span>
          <StatusBadge status={p.status} />
        </div>

        <p className="m-0 mb-3 text-[12.5px] leading-[1.5] text-[var(--color-text-secondary)] line-clamp-2 min-h-[38px]">
          {p.description || t('prompts.noDescription')}
        </p>

        <div className="flex gap-1 flex-wrap mb-3">
          <Tag>{p.category}</Tag>
          <MonoBadge>{p.version}</MonoBadge>
        </div>

        <div
          className="flex items-center pt-3 border-t border-[var(--color-border)]"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="ml-auto flex items-center gap-1">
            <ActionButton
              title={t('prompts.list.edit')}
              hoverVar="--color-accent"
              onClick={() => onEdit(p)}
            >
              <Pencil size={12} />
            </ActionButton>
            <ActionButton
              title={t('prompts.list.history')}
              hoverVar="--color-accent-soft"
              onClick={() => onHistory(p)}
            >
              <History size={12} />
            </ActionButton>
            <ActionButton
              title={t('prompts.list.delete')}
              hoverVar="--color-danger"
              onClick={() => onDelete(p)}
            >
              <Trash2 size={12} />
            </ActionButton>
          </div>
        </div>
      </div>
    );
  };

  return (
    <DataGrid<PromptItem>
      items={prompts}
      itemKey={(p) => p.id}
      renderItem={renderCard}
    />
  );
}
