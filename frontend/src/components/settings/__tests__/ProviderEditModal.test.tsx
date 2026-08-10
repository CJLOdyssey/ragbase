import { fetchModelsFromProvider } from '../../../api/client/keys';
import { listProviders } from '../../../api/client/providers';
import ProviderEditModal, { type ApiProviderForm } from '../ProviderEditModal';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../../api/client/providers', () => ({
  listProviders: vi.fn(() =>
    Promise.resolve({
      openai: {
        name: 'OpenAI',
        base_url: 'https://api.openai.com/v1',
        capabilities: ['chat', 'vector'],
        docs_url: null,
      },
    }),
  ),
}));

vi.mock('../../../api/client/keys', () => ({
  fetchModelsFromProvider: vi.fn(),
}));

const BASE_PROVIDER: ApiProviderForm = {
  id: 'key-1',
  provider: 'openai',
  capabilities: ['llm'],
  name: 'OpenAI',
  baseUrl: '',
  apiKey: 'sk-test',
  models: [],
  isActive: true,
};

describe('ProviderEditModal 模型刷新链路', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetch-models 失败时显示错误 banner，可关闭', async () => {
    vi.mocked(fetchModelsFromProvider).mockResolvedValue({
      success: false,
      models: [],
      message: 'Connection refused',
    });

    render(
      <ProviderEditModal
        provider={BASE_PROVIDER}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    const refreshBtn = screen.getByTitle('从 API 获取模型');
    fireEvent.click(refreshBtn);

    await waitFor(() =>
      expect(screen.getByText('Connection refused')).toBeInTheDocument(),
    );
    expect(screen.getByText('Connection refused').closest('div')).toBeTruthy();
  });

  it('fetch-models 成功时合并模型且不显示错误', async () => {
    vi.mocked(fetchModelsFromProvider).mockResolvedValue({
      success: true,
      models: ['gpt-4'],
    });

    render(
      <ProviderEditModal
        provider={BASE_PROVIDER}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByTitle('从 API 获取模型'));

    await waitFor(() => expect(screen.getByText('gpt-4')).toBeInTheDocument());
    expect(screen.queryByText('Connection refused')).toBeNull();
  });

  it('fetch-models 网络异常时显示错误 banner', async () => {
    vi.mocked(fetchModelsFromProvider).mockRejectedValue(
      new Error('Network Error'),
    );

    render(
      <ProviderEditModal
        provider={BASE_PROVIDER}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByTitle('从 API 获取模型'));

    await waitFor(() =>
      expect(screen.getByText('Network Error')).toBeInTheDocument(),
    );
  });

  it('同 provider 编辑时保留存储的 capabilities', async () => {
    const onSave = vi.fn();
    render(
      <ProviderEditModal
        provider={BASE_PROVIDER}
        onSave={onSave}
        onClose={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByText('保存'));

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        provider: 'openai',
        capabilities: ['llm'],
      }),
    );
  });

  it('切换 provider 时从目录派生 capabilities', async () => {
    vi.mocked(listProviders).mockResolvedValue({
      openai: {
        name: 'OpenAI',
        base_url: 'https://api.openai.com/v1',
        capabilities: ['chat', 'vector'],
        docs_url: null,
      },
      deepseek: {
        name: 'DeepSeek',
        base_url: 'https://api.deepseek.com/v1',
        capabilities: ['chat'],
        docs_url: null,
      },
    });
    const onSave = vi.fn();
    render(
      <ProviderEditModal
        provider={{ ...BASE_PROVIDER, capabilities: ['llm', 'embedding'] }}
        onSave={onSave}
        onClose={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.queryByRole('option', { name: 'DeepSeek' })).toBeTruthy();
    });
    fireEvent.change(screen.getByRole('combobox'), {
      target: { value: 'deepseek' },
    });
    fireEvent.click(screen.getByText('保存'));

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        provider: 'deepseek',
        capabilities: ['llm'],
      }),
    );
  });

  it('新 key 保存时从目录派生 capabilities', async () => {
    const onSave = vi.fn();
    render(
      <ProviderEditModal
        provider={{ ...BASE_PROVIDER, id: '' }}
        onSave={onSave}
        onClose={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByText('保存'));

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        capabilities: ['llm', 'embedding'],
      }),
    );
  });

  it('目录无此 provider 时回退到存储的 capabilities', async () => {
    vi.mocked(listProviders).mockResolvedValue({
      custom: {
        name: '自定义',
        base_url: '',
        capabilities: ['chat', 'vector'],
        docs_url: null,
      },
    });
    const onSave = vi.fn();
    render(
      <ProviderEditModal
        provider={BASE_PROVIDER}
        onSave={onSave}
        onClose={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.queryByRole('option', { name: 'OpenAI' })).toBeNull();
    });
    fireEvent.click(screen.getByText('保存'));

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ capabilities: ['llm'] }),
    );
  });
});
