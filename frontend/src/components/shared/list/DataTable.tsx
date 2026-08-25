/**
 * DataTable — column-config driven table shell.
 *
 * Visual baseline: AssetsTable (uppercase mono headers, accent-4% row hover,
 * 14px rounded container, overflow-visible for portal menus).
 *
 * OCP: new list pages pass column config — shell never changes.
 * ISP: cells render via `renderCell` delegation, so feature-specific
 * content (progress bars, menus) never leaks into the shell.
 */
import type { ReactNode } from 'react';

export interface DataTableColumn {
  /** Unique key; also the value passed to onSort. */
  key: string;
  /** Already-translated header text — or a custom node (e.g. select-all checkbox). */
  header: string | ReactNode;
  /** CSS grid track, e.g. '84px' | 'minmax(160px,1.5fr)'. Default '1fr'. */
  width?: string;
  sortable?: boolean;
  /** Center the header cell (first column defaults to start-aligned). */
  center?: boolean;
}

interface DataTableProps<T> {
  rows: T[];
  columns: DataTableColumn[];
  rowKey: (row: T) => string;
  renderCell: (row: T, col: DataTableColumn, colIndex: number) => ReactNode;
  onRowClick?: (row: T) => void;
  rowTestId?: (row: T) => string;
  sortField?: string | null;
  sortDir?: 'asc' | 'desc';
  onSort?: (field: string) => void;
  /** Rendered when rows is empty. */
  emptyState?: ReactNode;
}

function SortArrow({
  active,
  dir,
}: {
  active: boolean;
  dir: 'asc' | 'desc' | undefined;
}) {
  return (
    <span
      className={`ml-1 text-[10px] ${active ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-tertiary)]'}`}
    >
      {active ? (dir === 'asc' ? '↑' : '↓') : '↕'}
    </span>
  );
}

export default function DataTable<T>({
  rows,
  columns,
  rowKey,
  renderCell,
  onRowClick,
  rowTestId,
  sortField,
  sortDir,
  onSort,
  emptyState,
}: DataTableProps<T>) {
  const gridTemplateColumns = columns.map((c) => c.width ?? '1fr').join(' ');

  return (
    <div className="rounded-[14px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] overflow-visible">
      <div
        className="grid items-center h-10 px-[18px] border-b border-[var(--color-border-subtle)] bg-[color-mix(in_srgb,var(--color-surface-hover)_40%,transparent)]"
        style={{ gridTemplateColumns }}
      >
        {columns.map((col, i) => (
          <div
            key={col.key}
            onClick={() => {
              if (col.sortable && onSort) onSort(col.key);
            }}
            className={`text-[10.5px] font-semibold tracking-[0.07em] uppercase font-mono text-[var(--color-text-tertiary)] flex items-center ${i === 0 && !col.center ? 'justify-start' : 'justify-center text-center'} ${col.sortable && onSort ? 'cursor-pointer hover:text-[var(--color-text-secondary)]' : ''}`}
          >
            {col.header}
            {col.sortable && onSort && (
              <SortArrow active={sortField === col.key} dir={sortDir} />
            )}
          </div>
        ))}
      </div>

      {rows.length === 0 && emptyState}

      {rows.map((row) => (
        <div
          key={rowKey(row)}
          onClick={() => onRowClick?.(row)}
          className="grid items-center px-[18px] h-[56px] border-b border-[var(--color-border-subtle)] hover:bg-[color-mix(in_srgb,var(--color-accent)_4%,transparent)] transition-colors cursor-pointer"
          style={{ gridTemplateColumns }}
          data-testid={rowTestId?.(row)}
        >
          {columns.map((col, i) => (
            <div key={col.key} className="min-w-0">
              {renderCell(row, col, i)}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
