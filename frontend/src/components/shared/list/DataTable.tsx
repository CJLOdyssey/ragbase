/**
 * DataTable — antd Table wrapper with project-specific styling.
 *
 * OCP: new list pages pass column config — shell never changes.
 * ISP: cells render via `renderCell` delegation, so feature-specific
 * content (progress bars, menus) never leaks into the shell.
 */
import { ConfigProvider, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { ReactNode } from 'react';

export interface DataTableColumn {
  /** Unique key; also the value passed to onSort. */
  key: string;
  /** Already-translated header text — or a custom node (e.g. select-all checkbox). */
  header: string | ReactNode;
  /** CSS grid track, e.g. '84px' | 'minmax(160px,1.5fr)'. Default '1fr'. */
  width?: string;
  sortable?: boolean;
  /** Center the header and cell content. */
  center?: boolean;
}

/**
 * Parse CSS grid track to antd-compatible width.
 * '84px' → 84, 'minmax(160px,1.5fr)' → 160, '1fr' → undefined, '4fr' → undefined.
 */
function parseWidth(width?: string): number | undefined {
  if (!width) return undefined;
  const pxMatch = width.match(/^(\d+)px$/);
  if (pxMatch) return Number(pxMatch[1]);
  const minmaxMatch = width.match(/minmax\((\d+)px/);
  if (minmaxMatch) return Number(minmaxMatch[1]);
  // fr units are not supported by antd Table, return undefined to use default
  return undefined;
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
  /** Additional className for the outer container. */
  className?: string;
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
  className,
}: DataTableProps<T>) {
  const antdColumns: ColumnsType<T> = columns.map((col, i) => ({
    title: col.header,
    key: col.key,
    width: parseWidth(col.width),
    align: col.center ? 'center' : undefined,
    sorter: col.sortable,
    sortOrder:
      col.sortable && sortField === col.key
        ? sortDir === 'asc'
          ? 'ascend'
          : 'descend'
        : undefined,
    render: (_value: unknown, record: T) => (
      <div className="min-w-0">{renderCell(record, col, i)}</div>
    ),
  }));

  return (
    <ConfigProvider
      theme={{
        token: {
          colorBgContainer: 'var(--color-surface-raised)',
          colorBorderSecondary: 'var(--color-border-subtle)',
          colorText: 'var(--color-text-primary)',
          colorTextSecondary: 'var(--color-text-secondary)',
        },
        components: {
          Table: {
            headerBg: 'color-mix(in srgb, var(--color-surface-hover) 40%, transparent)',
            headerColor: 'var(--color-text-tertiary)',
            rowHoverBg: 'color-mix(in srgb, var(--color-accent) 4%, transparent)',
            borderColor: 'var(--color-border-subtle)',
            cellPaddingBlock: 0,
            cellPaddingInline: 18,
            headerBorderRadius: 14,
          },
        },
      }}
    >
      <div className="overflow-x-auto">
        <Table<T>
          className={className}
          columns={antdColumns}
          dataSource={rows}
          rowKey={rowKey}
          pagination={false}
          size="small"
          // 移动端：表格按内容最窄宽度渲染，由外层容器横向滚动
          // （antd scroll prop 会复制表头导致文本重复，改用 CSS 方案）
          style={{ minWidth: 'max-content' }}
          onChange={(_pagination, _filters, sorter) => {
            if (!onSort) return;
            const s = Array.isArray(sorter) ? sorter[0] : sorter;
            if (s?.columnKey != null && s.order) {
              onSort(String(s.columnKey));
            }
          }}
        onRow={(record) => ({
          onClick: () => onRowClick?.(record),
          'data-testid': rowTestId?.(record),
        })}
        locale={{
          emptyText: emptyState ?? undefined,
        }}
        />
      </div>
    </ConfigProvider>
  );
}
