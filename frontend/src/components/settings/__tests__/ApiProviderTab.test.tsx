import type { KeyItem } from '../../../api/client';
import ApiProviderTab from '../ApiProviderTab';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

const BASE_KEY: KeyItem = {
  id: 'k1',
  provider: 'openai',
  capabilities: ['llm'],
  label: 'OpenAI Key',
  key_masked: 'sk-***abc',
  base_url: null,
  models: ['gpt-4'],
  is_active: true,
  is_default: false,
  last_used_at: null,
  created_at: '2026-08-06T00:00:00Z',
};

function makeKey(overrides: Partial<KeyItem> & { capabilities?: string[] }) {
  return { ...BASE_KEY, ...overrides };
}

const baseProps = {
  keys: [BASE_KEY] as KeyItem[],
  loading: false as boolean,
  error: null as string | null,
  testingId: null as string | null,
  onAdd: vi.fn(),
  onEdit: vi.fn(),
  onToggleActive: vi.fn(),
  onTest: vi.fn(),
  onDelete: vi.fn(),
  onDismissError: vi.fn(),
};

function renderTab(overrides: Partial<typeof baseProps> = {}) {
  return render(<ApiProviderTab {...baseProps} {...overrides} />);
}

describe('ApiProviderTab', { tags: ['unit'] }, () => {
  it('renders key list with capability badges', () => {
    renderTab({
      keys: [
        makeKey({ capabilities: ['llm', 'embedding'] }),
        makeKey({ id: 'k2', label: 'Tavily Key', capabilities: ['tool'] }),
      ],
    });
    expect(screen.getByText('OpenAI Key')).toBeInTheDocument();
    expect(screen.getByText('Tavily Key')).toBeInTheDocument();
    expect(screen.getByText('providerEdit.badge.llm')).toBeInTheDocument();
    expect(screen.getByText('providerEdit.badge.tool')).toBeInTheDocument();
  });

  it('filters rows by capability category', () => {
    renderTab({
      keys: [
        makeKey({ capabilities: ['llm', 'embedding'] }),
        makeKey({ id: 'k2', label: 'Tavily Key', capabilities: ['tool'] }),
      ],
    });
    fireEvent.click(screen.getByText('providerEdit.category.tool'));
    expect(screen.getByText('Tavily Key')).toBeInTheDocument();
    expect(screen.queryByText('OpenAI Key')).toBeNull();
  });

  it('shows all rows again after switching back to 全部', () => {
    renderTab({
      keys: [
        makeKey({ capabilities: ['llm'] }),
        makeKey({ id: 'k2', label: 'Tavily Key', capabilities: ['tool'] }),
      ],
    });
    fireEvent.click(screen.getByText('providerEdit.category.tool'));
    expect(screen.queryByText('OpenAI Key')).toBeNull();
    fireEvent.click(screen.getByText('providerEdit.filterAll'));
    expect(screen.getByText('OpenAI Key')).toBeInTheDocument();
    expect(screen.getByText('Tavily Key')).toBeInTheDocument();
  });

  it('clears row selection when switching filter tab', () => {
    const onBatchDelete = vi.fn();
    renderTab({
      keys: [
        makeKey({ capabilities: ['llm'] }),
        makeKey({ id: 'k2', label: 'Tavily Key', capabilities: ['tool'] }),
      ],
      onBatchDelete,
    });

    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[2]);
    expect(screen.getByText('confirm.delete (1)')).toBeInTheDocument();

    fireEvent.click(screen.getByText('providerEdit.category.tool'));
    expect(screen.queryByText('confirm.delete (1)')).toBeNull();

    fireEvent.click(screen.getByText('providerEdit.filterAll'));
    expect(screen.queryByText('confirm.delete (1)')).toBeNull();
    expect(onBatchDelete).not.toHaveBeenCalled();
  });

  it('batch delete sends all selected row ids', () => {
    const onBatchDelete = vi.fn();
    renderTab({
      keys: [
        makeKey({ capabilities: ['llm'] }),
        makeKey({ id: 'k2', label: 'Tavily Key', capabilities: ['tool'] }),
      ],
      onBatchDelete,
    });
    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[1]);
    fireEvent.click(checkboxes[2]);
    expect(screen.getByText('confirm.delete (2)')).toBeInTheDocument();
    fireEvent.click(screen.getByText('confirm.delete (2)'));
    expect(onBatchDelete).toHaveBeenCalledWith(['k1', 'k2']);
  });

  it('batch activate enables and disables selected rows via onBatchToggleActive', () => {
    const onBatchToggleActive = vi.fn();
    renderTab({
      keys: [
        makeKey({ capabilities: ['llm'] }),
        makeKey({ id: 'k2', label: 'Tavily Key', capabilities: ['tool'] }),
      ],
      onBatchToggleActive,
    });
    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[1]);
    fireEvent.click(screen.getByText('providerEdit.disable (1)'));
    expect(onBatchToggleActive).toHaveBeenCalledWith(['k1'], false);
    // 批量操作后选择被清空，需重新勾选
    fireEvent.click(checkboxes[1]);
    fireEvent.click(screen.getByText('providerEdit.enable (1)'));
    expect(onBatchToggleActive).toHaveBeenCalledWith(['k1'], true);
  });

  it('falls back to per-row callbacks when batch handlers are absent', () => {
    const onDelete = vi.fn();
    const onToggleActive = vi.fn();
    renderTab({
      keys: [makeKey({ capabilities: ['llm'] })],
      onDelete,
      onToggleActive,
    });
    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[1]);
    fireEvent.click(screen.getByText('confirm.delete (1)'));
    expect(onDelete).toHaveBeenCalledWith('k1');
    fireEvent.click(checkboxes[1]);
    fireEvent.click(screen.getByText('providerEdit.disable (1)'));
    expect(onToggleActive).toHaveBeenCalledWith('k1', false);
  });

  it('renders the error banner and dismisses it', () => {
    const onDismissError = vi.fn();
    renderTab({ error: 'boom', onDismissError });
    expect(screen.getByText('boom')).toBeInTheDocument();
    fireEvent.click(screen.getByText('✕'));
    expect(onDismissError).toHaveBeenCalled();
  });

  it('paginates when there are more than pageSize keys', () => {
    const keys = Array.from({ length: 9 }, (_, i) =>
      makeKey({ id: `k${i}`, label: `Key ${i}`, capabilities: ['llm'] }),
    );
    renderTab({ keys });
    expect(screen.getByText('Key 0')).toBeInTheDocument();
    expect(screen.queryByText('Key 8')).toBeNull();
    // 翻页：点击 antd Pagination 下一页 → 第二页显示 Key 8
    const nextBtn = document.querySelector(
      '.ant-pagination-next button',
    ) as HTMLButtonElement;
    fireEvent.click(nextBtn);
    expect(screen.getByText('Key 8')).toBeInTheDocument();
    expect(screen.queryByText('Key 0')).toBeNull();
    // 翻回第一页
    const prevBtn = document.querySelector(
      '.ant-pagination-prev button',
    ) as HTMLButtonElement;
    fireEvent.click(prevBtn);
    expect(screen.getByText('Key 0')).toBeInTheDocument();
  });

  it('disables the test button while testing the row', () => {
    renderTab({ testingId: 'k1' });
    // switch(0) + edit(1) + test(2) + delete(3)
    const row = screen.getByText('OpenAI Key').closest('tr')!;
    const buttons = Array.from(row.querySelectorAll('button'));
    expect((buttons[2] as HTMLButtonElement).disabled).toBe(true);
  });

  it('renders the empty state when there are no keys', () => {
    renderTab({ keys: [] });
    expect(screen.getByText(/api\.noKeys/)).toBeInTheDocument();
  });
});
