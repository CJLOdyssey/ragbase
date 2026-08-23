import { TestProviders } from '../../../../test/setup';
import DataTable, { type DataTableColumn } from '../DataTable';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

interface Row {
  id: string;
  name: string;
  size: number;
}

const rows: Row[] = [
  { id: 'a', name: 'alpha.md', size: 1 },
  { id: 'b', name: 'beta.md', size: 2 },
];

const columns: DataTableColumn<Row>[] = [
  { key: 'name', header: '文件名', width: 'minmax(160px,1.5fr)', sortable: true },
  { key: 'size', header: '大小', width: '84px' },
];

function renderTable(overrides: Record<string, unknown> = {}) {
  return render(
    <TestProviders>
      <DataTable
        rows={rows}
        columns={columns}
        rowKey={(r) => r.id}
        renderCell={(row, col) =>
          col.key === 'name' ? (
            <span title={row.name}>{row.name}</span>
          ) : (
            <span>{row.size} B</span>
          )
        }
        {...overrides}
      />
    </TestProviders>,
  );
}

describe('DataTable', { tags: ['unit'] }, () => {
  it('renders all headers and rows', () => {
    renderTable();
    expect(screen.getByText('文件名')).toBeInTheDocument();
    expect(screen.getByText('大小')).toBeInTheDocument();
    expect(screen.getByTitle('alpha.md')).toBeInTheDocument();
    expect(screen.getByTitle('beta.md')).toBeInTheDocument();
  });

  it('builds gridTemplateColumns from column widths', () => {
    const { container } = renderTable();
    const header = container.querySelector('.grid.h-10') as HTMLElement;
    expect(header.style.gridTemplateColumns).toBe('minmax(160px,1.5fr) 84px');
  });

  it('sortable header triggers onSort with column key', () => {
    const onSort = vi.fn();
    const { container } = renderTable({ onSort });
    const nameHeader = screen.getByText('文件名');
    fireEvent.click(nameHeader);
    expect(onSort).toHaveBeenCalledWith('name');
    // sort arrow present on sortable column only
    expect(container.querySelectorAll('.ml-1.text-\\[10px\\]').length).toBe(1);
  });

  it('non-sortable header does not trigger onSort', () => {
    const onSort = vi.fn();
    renderTable({ onSort });
    fireEvent.click(screen.getByText('大小'));
    expect(onSort).not.toHaveBeenCalled();
  });

  it('sort arrow direction follows sortDir when active', () => {
    renderTable({ sortField: 'name', sortDir: 'desc', onSort: () => {} });
    const arrow = screen.getByText('↓');
    expect(arrow).toBeInTheDocument();
  });

  it('row click delegates to onRowClick; testid applied', () => {
    const onRowClick = vi.fn();
    renderTable({
      onRowClick,
      rowTestId: (r) => `item-${r.id}`,
    });
    fireEvent.click(screen.getByTestId('item-b'));
    expect(onRowClick).toHaveBeenCalledWith(rows[1]);
  });

  it('renders emptyState when no rows', () => {
    renderTable({ rows: [], emptyState: <div>暂无数据</div> });
    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });

  it('header style matches assets baseline (uppercase mono, centered non-first)', () => {
    renderTable();
    const h1 = screen.getByText('文件名');
    const h2 = screen.getByText('大小');
    expect(h1.className).toContain('justify-start');
    expect(h2.className).toContain('justify-center');
    expect(h1.className).toContain('uppercase');
    expect(h1.className).toContain('font-mono');
  });
});
