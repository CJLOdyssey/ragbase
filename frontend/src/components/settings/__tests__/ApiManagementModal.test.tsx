import type { KeyItem } from '../../../api/client';
import { TestProviders } from '../../../test/setup';
import ApiManagementModal from '../ApiManagementModal';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string, opts?: { name?: string; count?: number }) =>
      `${k}${opts?.name ? ':' + opts.name : ''}${opts?.count ? ':' + opts.count : ''}`,
    i18n: { language: 'zh-CN' },
  }),
}));

const apiMocks = vi.hoisted(() => ({
  listKeys: vi.fn(),
  createKey: vi.fn(),
  updateKey: vi.fn(),
  deleteKey: vi.fn(),
  testKeyConnection: vi.fn(),
  getKeyUsage: vi.fn(),
  listModels: vi.fn(),
  listProviders: vi.fn(),
  fetchModelsFromProvider: vi.fn(),
}));

vi.mock('../../../api/client/keys', () => apiMocks);
vi.mock('../../../api/client/models', () => ({
  listModels: apiMocks.listModels,
}));
vi.mock('../../../api/client/providers', () => ({
  listProviders: apiMocks.listProviders,
}));

const KEY: KeyItem = {
  id: 'k1',
  provider: 'openai',
  capabilities: ['llm'],
  label: 'OpenAI 主',
  key_masked: 'sk-...1234',
  base_url: '',
  models: ['gpt-4'],
  is_active: true,
  is_default: true,
  last_used_at: null,
  created_at: null,
};

function renderModal() {
  return render(
    <TestProviders>
      <ApiManagementModal onClose={vi.fn()} />
    </TestProviders>,
  );
}

// antd Tooltip 不渲染原生 title 属性，改用行内操作按钮定位（列顺序：
// status(Switch) / edit / test / delete，过滤掉 role=switch 的按钮）。
function rowActionButtons(rowText: string): HTMLElement[] {
  const row = screen.getByText(rowText).closest('tr')!;
  return Array.from(row.querySelectorAll('button')).filter(
    (b) => b.getAttribute('role') !== 'switch',
  );
}

describe('ApiManagementModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    apiMocks.listKeys.mockResolvedValue([KEY]);
    apiMocks.getKeyUsage.mockResolvedValue({
      today_requests: 10,
      today_tokens: 20,
      month_requests: 30,
      month_tokens: 40,
    });
    apiMocks.listModels.mockResolvedValue([{ id: 'gpt-4', type: 'llm' }]);
    apiMocks.listProviders.mockResolvedValue({
      openai: {
        name: 'OpenAI',
        base_url: '',
        capabilities: ['llm'],
        docs_url: null,
      },
    });
    apiMocks.fetchModelsFromProvider.mockResolvedValue({
      success: true,
      models: [],
    });
    apiMocks.createKey.mockResolvedValue({});
    apiMocks.updateKey.mockResolvedValue({});
    apiMocks.deleteKey.mockResolvedValue({});
    apiMocks.testKeyConnection.mockResolvedValue({
      success: true,
      message: '',
    });
    vi.spyOn(window, 'alert').mockImplementation(() => {});
  });

  it('renders the API keys tab with loaded keys', async () => {
    renderModal();
    expect(await screen.findByText('OpenAI 主')).toBeInTheDocument();
  });

  it('switches to the models tab and renders model selector', async () => {
    renderModal();
    fireEvent.click(await screen.findByText('api.tab_model'));
    expect(screen.getByText('gpt-4')).toBeInTheDocument();
  });

  it('switches to the usage tab and renders usage stats', async () => {
    renderModal();
    fireEvent.click(await screen.findByText('api.tab_usage'));
    expect(await screen.findByText('10')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
  });

  it('opens the add-key form and saves a new key', async () => {
    renderModal();
    fireEvent.click(await screen.findByText('providerEdit.addKey'));
    // ProviderEditModal opens — fill the API key input
    const apiKeyInput = await screen.findByPlaceholderText(
      'providerEdit.apiKeyPlaceholder',
    );
    fireEvent.change(apiKeyInput, { target: { value: 'sk-abcdefghijkl' } });
    fireEvent.click(screen.getByText('providerEdit.save'));
    await waitFor(() => expect(apiMocks.createKey).toHaveBeenCalled());
    expect(apiMocks.createKey).toHaveBeenCalledWith(
      expect.objectContaining({ api_key: 'sk-abcdefghijkl' }),
    );
  });

  it('shows duplicate-key error when masked key already exists', async () => {
    apiMocks.listKeys.mockResolvedValue([{ ...KEY, key_masked: 'sk-...ijkl' }]);
    renderModal();
    await screen.findByText('OpenAI 主');
    fireEvent.click(screen.getByText('providerEdit.addKey'));
    const apiKeyInput = await screen.findByPlaceholderText(
      'providerEdit.apiKeyPlaceholder',
    );
    fireEvent.change(apiKeyInput, { target: { value: 'sk-abcdefghijkl' } });
    fireEvent.click(screen.getByText('providerEdit.save'));
    expect(
      await screen.findByText('providerEdit.keyExists:OpenAI 主'),
    ).toBeInTheDocument();
    expect(apiMocks.createKey).not.toHaveBeenCalled();
  });

  it('edits an existing key and updates it', async () => {
    renderModal();
    await screen.findByText('OpenAI 主');
    const [editBtn] = rowActionButtons('OpenAI 主');
    fireEvent.click(editBtn);
    await waitFor(() =>
      expect(screen.getByText('providerEdit.save')).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByText('providerEdit.save'));
    await waitFor(() => expect(apiMocks.updateKey).toHaveBeenCalled());
    expect(apiMocks.updateKey).toHaveBeenCalledWith(
      'k1',
      expect.objectContaining({ label: 'OpenAI 主' }),
    );
  });

  it('toggles key active state', async () => {
    renderModal();
    await screen.findByText('OpenAI 主');
    const toggle = screen.getByRole('switch');
    fireEvent.click(toggle);
    await waitFor(() => expect(apiMocks.updateKey).toHaveBeenCalled());
    expect(apiMocks.updateKey).toHaveBeenCalledWith(
      'k1',
      expect.objectContaining({ is_active: false }),
    );
  });

  it('tests connection and alerts success', async () => {
    renderModal();
    await screen.findByText('OpenAI 主');
    const [, testBtn] = rowActionButtons('OpenAI 主');
    fireEvent.click(testBtn);
    await waitFor(() =>
      expect(window.alert).toHaveBeenCalledWith('api.testSuccess'),
    );
  });

  it('deletes a key via confirm modal', async () => {
    renderModal();
    await screen.findByText('OpenAI 主');
    const [, , delBtn] = rowActionButtons('OpenAI 主');
    fireEvent.click(delBtn);
    await waitFor(() =>
      expect(
        screen.getByText('providerEdit.deleteKeyConfirm'),
      ).toBeInTheDocument(),
    );
    const confirmBtn = screen.getAllByText('confirm.confirm')[0] as HTMLElement;
    fireEvent.click(confirmBtn);
    await waitFor(() => expect(apiMocks.deleteKey).toHaveBeenCalledWith('k1'));
  });
});
