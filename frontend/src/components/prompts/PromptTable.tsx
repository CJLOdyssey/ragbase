import { DataTable, type DataTableColumn } from '../shared/list';
import { ActionButton } from '../shared/list/badges';
import { History, Pencil, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { PromptItem } from '../../api/client/prompts';
import { MonoBadge, StatusBadge, Tag } from './PromptBadges';

interface Props {
  prompts: PromptItem[];
  onEdit: (row: PromptItem) => void;
  onDelete: (row: PromptItem) => void;
  onHistory: (row: PromptItem) => void;
  onSelect: (id: string) => void;
}

/** Centered cell wrapper matching assets visual baseline. */
function CellCenter({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-center text-center min-w-0">
      {children}
    </div>
  );
}

export default function PromptTable({
  prompts,
  onEdit,
  onDelete,
  onHistory,
  onSelect,
}: Props) {
  const { t } = useTranslation();

  const columns: DataTableColumn[] = [
    { key: 'name', header: t('prompts.table.name'), width: '4fr' },
    { key: 'desc', header: t('prompts.table.desc'), width: '2.5fr' },
    {
      key: 'category',
      header: t('prompts.table.category'),
      width: 'minmax(80px,1fr)',
      center: true,
    },
    {
      key: 'status',
      header: t('prompts.table.status'),
      width: 'minmax(72px,1fr)',
      center: true,
    },
    {
      key: 'version',
      header: t('prompts.table.version'),
      width: 'minmax(88px,1fr)',
      center: true,
    },
    {
      key: 'actions',
      header: t('prompts.table.actions'),
      width: 'minmax(88px,1fr)',
      center: true,
    },
  ];

  const renderCell = (
    row: PromptItem,
    col: DataTableColumn,
  ): React.ReactNode => {
    switch (col.key) {
      case 'name':
        return (
          <div className="min-w-0 pr-3">
            <div
              className="text-[13.5px] font-medium text-[var(--color-text-primary)] mb-0.5 truncate"
              title={row.name}
            >
              {row.name}
            </div>
          </div>
        );
      case 'desc':
        return (
          <div
            className="text-[12.5px] text-[var(--color-text-secondary)] truncate pr-3"
            title={row.description || ''}
          >
            {row.description || '—'}
          </div>
        );
      case 'category':
        return (
          <CellCenter>
            <Tag>{row.category}</Tag>
          </CellCenter>
        );
      case 'status':
        return (
          <CellCenter>
            <StatusBadge status={row.status} />
          </CellCenter>
        );
      case 'version':
        return (
          <CellCenter>
            <MonoBadge>{row.version}</MonoBadge>
          </CellCenter>
        );
      case 'actions':
        return (
          <div className="flex gap-1 justify-center">
            <ActionButton
              title={t('prompts.list.edit')}
              hoverVar="--color-accent"
              onClick={() => onEdit(row)}
            >
              <Pencil size={12} />
            </ActionButton>
            <ActionButton
              title={t('prompts.list.history')}
              hoverVar="--color-accent-soft"
              onClick={() => onHistory(row)}
            >
              <History size={12} />
            </ActionButton>
            <ActionButton
              title={t('prompts.list.delete')}
              hoverVar="--color-danger"
              onClick={() => onDelete(row)}
            >
              <Trash2 size={12} />
            </ActionButton>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <DataTable<PromptItem>
      rows={prompts}
      columns={columns}
      rowKey={(p) => p.id}
      renderCell={(row, col) => renderCell(row, col)}
      onRowClick={(p) => onSelect(p.id)}
    />
  );
}
