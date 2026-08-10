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
    expect(screen.getByText('删除 (1)')).toBeInTheDocument();

    fireEvent.click(screen.getByText('providerEdit.category.tool'));
    expect(screen.queryByText('删除 (1)')).toBeNull();

    fireEvent.click(screen.getByText('providerEdit.filterAll'));
    expect(screen.queryByText('删除 (1)')).toBeNull();
    expect(onBatchDelete).not.toHaveBeenCalled();
  });
});
