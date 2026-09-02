import type { KeyItem } from '../../../api/client';
import { TestProviders } from '../../../test/setup';
import { useApiKeys } from '../useApiKeys';
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string, opts?: { name?: string }) =>
      `${k}${opts?.name ? ':' + opts.name : ''}`,
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
}));

vi.mock('../../../api/client/keys', () => apiMocks);
vi.mock('../../../api/client/models', () => ({
  listModels: apiMocks.listModels,
}));

const KEY: KeyItem = {
  id: 'k1',
  provider: 'openai',
  capabilities: ['llm'],
  label: 'OpenAI 主',
  key_masked: 'sk-...1234',
  base_url: 'https://api.openai.com/v1',
  models: ['gpt-4'],
  is_active: true,
  is_default: true,
  last_used_at: null,
  created_at: null,
};

function renderApi() {
  return renderHook(() => useApiKeys(), { wrapper: TestProviders });
}

describe('useApiKeys', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    apiMocks.listKeys.mockResolvedValue([KEY]);
    apiMocks.getKeyUsage.mockResolvedValue({
      today_requests: 1,
      today_tokens: 2,
      month_requests: 3,
      month_tokens: 4,
    });
    apiMocks.listModels.mockResolvedValue([{ id: 'gpt-4', type: 'llm' }]);
    apiMocks.createKey.mockResolvedValue({});
    apiMocks.updateKey.mockResolvedValue({});
    apiMocks.deleteKey.mockResolvedValue({});
    apiMocks.testKeyConnection.mockResolvedValue({
      success: true,
      message: '',
    });
    vi.spyOn(window, 'alert').mockImplementation(() => {});
  });

  it('loads keys, usage and model types on mount', async () => {
    const { result } = renderApi();
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.keys).toEqual([KEY]);
    expect(result.current.usage.today_requests).toBe(1);
    expect(result.current.allModels).toEqual([
      { model: 'gpt-4', keyId: 'k1', type: 'llm' },
    ]);
  });

  it('showAddForm seeds a new key and marks first key as default', async () => {
    const { result } = renderApi();
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => result.current.showAddForm());
    expect(result.current.editingKey).toMatchObject({
      id: '',
      provider: 'openai',
      is_default: false,
    });
  });

  it('handleSaveKey creates a key and refreshes the list', async () => {
    const { result } = renderApi();
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => {
      await result.current.handleSaveKey({
        provider: 'openai',
        capabilities: ['llm'],
        label: 'New Key',
        apiKey: 'sk-abcdefghijkl',
        baseUrl: '',
        models: [],
      });
    });
    expect(apiMocks.createKey).toHaveBeenCalledWith(
      expect.objectContaining({ label: 'New Key', api_key: 'sk-abcdefghijkl' }),
    );
    expect(apiMocks.listKeys).toHaveBeenCalled();
    expect(result.current.editingKey).toBeNull();
  });

  it('handleSaveKey rejects duplicate masked keys', async () => {
    // maskKey('sk-abcdefghijkl') = 'sk-...ijkl' —— 与已有 key 的 key_masked 相同 → 判重
    apiMocks.listKeys.mockResolvedValue([{ ...KEY, key_masked: 'sk-...ijkl' }]);
    const { result } = renderApi();
    await waitFor(() => expect(result.current.keys.length).toBe(1));
    await act(async () => {
      await result.current.handleSaveKey({
        provider: 'openai',
        capabilities: [],
        label: 'dup',
        apiKey: 'sk-abcdefghijkl',
        baseUrl: '',
        models: [],
      });
    });
    expect(apiMocks.createKey).not.toHaveBeenCalled();
    expect(result.current.modalError).toContain('providerEdit.keyExists');
  });

  it('handleSaveKey surfaces create failures as modalError (弹窗内可见)', async () => {
    apiMocks.createKey.mockRejectedValue(new Error('boom'));
    const { result } = renderApi();
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => {
      await result.current.handleSaveKey({
        provider: 'openai',
        capabilities: [],
        label: 'x',
        apiKey: 'sk-abcdefghijkl',
        baseUrl: '',
        models: [],
      });
    });
    // 保存失败走 modalError（弹窗内横幅）；写 error 会被弹窗遮住，误导用户
    expect(result.current.modalError).toBe('boom');
  });

  it('handleUpdateKey updates and reloads keys', async () => {
    const { result } = renderApi();
    await waitFor(() => expect(result.current.loading).toBe(false));
    const ok = await act(async () => {
      return result.current.handleUpdateKey('k1', { isActive: false });
    });
    expect(ok).toBe(true);
    expect(apiMocks.updateKey).toHaveBeenCalledWith(
      'k1',
      expect.objectContaining({ is_active: false }),
    );
  });

  it('handleUpdateKey returns false on failure', async () => {
    apiMocks.updateKey.mockRejectedValue(new Error('up-boom'));
    const { result } = renderApi();
    await waitFor(() => expect(result.current.loading).toBe(false));
    const ok = await act(async () => {
      return result.current.handleUpdateKey('k1', { isActive: false });
    });
    expect(ok).toBe(false);
    expect(result.current.error).toBe('up-boom');
  });

  it('handleDeleteKey opens confirm and confirmDeleteAction deletes', async () => {
    const { result } = renderApi();
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => result.current.handleDeleteKey('k1'));
    expect(result.current.confirmDeleteIds).toEqual(['k1']);
    await act(async () => {
      await result.current.confirmDeleteAction();
    });
    expect(apiMocks.deleteKey).toHaveBeenCalledWith('k1');
    expect(result.current.confirmDeleteIds).toBeNull();
  });

  it('confirmDeleteAction is a no-op without pending ids', async () => {
    const { result } = renderApi();
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => {
      await result.current.confirmDeleteAction();
    });
    expect(apiMocks.deleteKey).not.toHaveBeenCalled();
  });

  it('handleBatchDelete deletes all selected keys', async () => {
    const { result } = renderApi();
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => result.current.handleBatchDelete(['k1', 'k2']));
    await act(async () => {
      await result.current.confirmDeleteAction();
    });
    expect(apiMocks.deleteKey).toHaveBeenCalledTimes(2);
  });

  it('handleTestConnection alerts success and failure', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
    const { result } = renderApi();
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => {
      await result.current.handleTestConnection(KEY);
    });
    expect(alertSpy).toHaveBeenCalledWith('api.testSuccess');
    expect(result.current.testingId).toBeNull();

    apiMocks.testKeyConnection.mockResolvedValue({
      success: false,
      message: 'denied',
    });
    await act(async () => {
      await result.current.handleTestConnection(KEY);
    });
    expect(alertSpy).toHaveBeenCalledWith('api.testFail: denied');

    apiMocks.testKeyConnection.mockRejectedValue(new Error('net'));
    await act(async () => {
      await result.current.handleTestConnection(KEY);
    });
    expect(alertSpy).toHaveBeenCalledWith('api.testError');
  });

  it('handleModelSelect persists selection and dispatches event', async () => {
    const dispatchSpy = vi.spyOn(window, 'dispatchEvent');
    const { result } = renderApi();
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => result.current.handleModelSelect('gpt-4'));
    expect(result.current.selectedModel).toBe('gpt-4');
    expect(localStorage.getItem('ragbase-selected-model')).toBe('gpt-4');
    expect(dispatchSpy).toHaveBeenCalledWith(expect.any(Event));
  });

  it('loads model selection from localStorage on init', async () => {
    localStorage.setItem('ragbase-selected-model', 'claude-3');
    const { result } = renderApi();
    expect(result.current.selectedModel).toBe('claude-3');
  });

  it('recovers from a failed key load without crashing', async () => {
    apiMocks.listKeys.mockRejectedValue(new Error('net'));
    const { result } = renderApi();
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.keys).toEqual([]);
  });
});
