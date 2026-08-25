import { listAssets } from '../../../api/client/assets';
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  listKnowledgeBases,
  updateKnowledgeBase,
} from '../../../api/client/knowledgeBases';
import KnowledgeBasePage from '../KnowledgeBasePage';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../../api/client/knowledgeBases', () => ({
  listKnowledgeBases: vi.fn(),
  createKnowledgeBase: vi.fn(),
  updateKnowledgeBase: vi.fn(),
  deleteKnowledgeBase: vi.fn(),
  assignAssetToKb: vi.fn(),
}));

vi.mock('../../../api/client/assets', () => ({
  listAssets: vi.fn(),
}));

vi.mock('../../../api/client/models', () => ({
  listModels: vi.fn().mockResolvedValue([
    {
      id: 'bge-m3',
      label: 'bge-m3',
      provider: 'siliconflow',
      type: 'embedding',
    },
    { id: 'gpt-4o', label: 'gpt-4o', provider: 'openai', type: 'llm' },
  ]),
}));

vi.mock('../../../api/client/ragTest', () => ({
  testRetrieval: vi.fn(),
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      changeLanguage: vi.fn(),
      language: 'zh-CN',
    },
  }),
}));

describe('KnowledgeBasePage', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    vi.clearAllMocks();
  });

  const renderWithClient = (ui: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{ui}</MemoryRouter>
      </QueryClientProvider>,
    );
  };

  it('renders knowledge base page title', async () => {
    vi.mocked(listKnowledgeBases).mockResolvedValue([]);
    vi.mocked(listAssets).mockResolvedValue([]);

    renderWithClient(<KnowledgeBasePage />);

    await waitFor(() => {
      expect(screen.getByText('kb.title')).toBeInTheDocument();
    });
  });

  it('displays create button', async () => {
    vi.mocked(listKnowledgeBases).mockResolvedValue([]);
    vi.mocked(listAssets).mockResolvedValue([]);

    renderWithClient(<KnowledgeBasePage />);

    await waitFor(() => {
      expect(screen.getByText('kb.create')).toBeInTheDocument();
    });
  });

  it('shows empty state when no knowledge bases', async () => {
    vi.mocked(listKnowledgeBases).mockResolvedValue([]);
    vi.mocked(listAssets).mockResolvedValue([]);

    renderWithClient(<KnowledgeBasePage />);

    await waitFor(() => {
      expect(screen.getByText('kb.noKbs')).toBeInTheDocument();
    });
  });

  it('renders knowledge base list', async () => {
    const mockKbs = [
      {
        id: 'kb-1',
        name: '测试知识库',
        description: '这是一个测试知识库',
        assetCount: 5,
        createdAt: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    ];

    vi.mocked(listKnowledgeBases).mockResolvedValue(mockKbs);
    vi.mocked(listAssets).mockResolvedValue([]);

    renderWithClient(<KnowledgeBasePage />);

    await waitFor(() => {
      expect(screen.getByText('测试知识库')).toBeInTheDocument();
      expect(screen.getByText('这是一个测试知识库')).toBeInTheDocument();
    });
  });

  it('opens create modal when clicking create button', async () => {
    vi.mocked(listKnowledgeBases).mockResolvedValue([]);
    vi.mocked(listAssets).mockResolvedValue([]);

    renderWithClient(<KnowledgeBasePage />);

    await waitFor(() => {
      const createButton = screen.getByText('kb.create');
      fireEvent.click(createButton);
    });

    await waitFor(() => {
      expect(screen.getByText('kb.createTitle')).toBeInTheDocument();
    });
  });

  it('creates new knowledge base', async () => {
    vi.mocked(listKnowledgeBases).mockResolvedValue([]);
    vi.mocked(listAssets).mockResolvedValue([]);
    vi.mocked(createKnowledgeBase).mockResolvedValue({
      id: 'new-kb',
      name: '新知识库',
      description: '描述',
      embedModel: 'bge-m3',
      createdAt: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    });

    renderWithClient(<KnowledgeBasePage />);

    await waitFor(() => {
      const createButton = screen.getByText('kb.create');
      fireEvent.click(createButton);
    });

    await waitFor(() => {
      expect(screen.getByText('kb.createTitle')).toBeInTheDocument();
    });

    // 通过role找到输入框
    const textInputs = screen.getAllByRole('textbox');
    const nameInput = textInputs[0];
    const descInput = textInputs[1];

    fireEvent.change(nameInput, { target: { value: '新知识库' } });
    fireEvent.change(descInput, { target: { value: '描述' } });

    // 等待嵌入模型列表加载并自动预填第一个可用 embedding 模型
    await waitFor(() => expect(screen.getByText('bge-m3')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'confirm.confirm' }));

    // 嵌入模型自动预填为第一个可用 embedding 模型（必选）
    await waitFor(() => {
      expect(createKnowledgeBase).toHaveBeenCalledWith(
        '新知识库',
        '描述',
        'bge-m3',
        { chunkSize: 512, overlap: 64 },
      );
    });
  });

  it('edits a knowledge base via edit modal', async () => {
    vi.mocked(listKnowledgeBases).mockResolvedValue([
      {
        id: 'kb-1',
        name: '测试知识库',
        description: '',
        embedModel: 'bge-m3',
        assetCount: 0,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      },
    ]);
    vi.mocked(listAssets).mockResolvedValue([]);
    vi.mocked(updateKnowledgeBase).mockResolvedValue({
      id: 'kb-1',
      name: '改名库',
      description: '',
      embedModel: 'bge-m3',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
    });

    renderWithClient(<KnowledgeBasePage />);

    await waitFor(() => {
      expect(screen.getByText('测试知识库')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('kb.edit'));

    await waitFor(() => {
      expect(screen.getByText('kb.editTitle')).toBeInTheDocument();
    });

    const nameInput = screen.getAllByRole('textbox')[0];
    // 等待表单预填 effect 完成后再改值，避免被覆盖
    await waitFor(() => expect(nameInput).toHaveValue('测试知识库'));
    fireEvent.change(nameInput, { target: { value: '改名库' } });

    // 编辑模式回填 kb.embedModel，等待其出现在 Select 中
    await waitFor(() =>
      expect(screen.getAllByText('bge-m3').length).toBeGreaterThan(0),
    );

    fireEvent.click(screen.getByRole('button', { name: 'confirm.confirm' }));

    await waitFor(() => {
      expect(updateKnowledgeBase).toHaveBeenCalledWith(
        'kb-1',
        '改名库',
        '',
        'bge-m3',
        { chunkSize: 512, overlap: 64 },
      );
    });
  });

  it('opens recall test as a centered modal', async () => {
    vi.mocked(listKnowledgeBases).mockResolvedValue([
      {
        id: 'kb-1',
        name: '测试库',
        description: '',
        embedModel: 'bge-m3',
        assetCount: 0,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      },
    ]);
    vi.mocked(listAssets).mockResolvedValue([]);

    renderWithClient(<KnowledgeBasePage />);

    await waitFor(() => {
      expect(screen.getByText('测试库')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('ragTest.button'));

    expect(
      await screen.findByText('ragTest.title · 测试库'),
    ).toBeInTheDocument();
  });

  it('deletes a knowledge base after confirmation', async () => {
    vi.mocked(listKnowledgeBases).mockResolvedValue([
      {
        id: 'kb-1',
        name: '待删除库',
        description: '',
        embedModel: 'bge-m3',
        assetCount: 0,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      },
    ]);
    vi.mocked(listAssets).mockResolvedValue([]);

    renderWithClient(<KnowledgeBasePage />);

    await waitFor(() => {
      expect(screen.getByText('待删除库')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('confirm.delete'));

    const confirmButton = await screen.findByRole('button', {
      name: 'confirm.confirm',
    });
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(deleteKnowledgeBase).toHaveBeenCalledWith('kb-1');
    });
  });

  it('shows uncategorized assets banner with count', async () => {
    vi.mocked(listKnowledgeBases).mockResolvedValue([]);
    vi.mocked(listAssets).mockResolvedValue([
      {
        id: 'asset-1',
        name: '未分类文档.pdf',
        type: 'pdf',
        size: 1024,
        createdAt: '2024-01-01T00:00:00Z',
        knowledgeBaseId: null,
      },
      {
        id: 'asset-2',
        name: '已分类文档.pdf',
        type: 'pdf',
        size: 1024,
        createdAt: '2024-01-01T00:00:00Z',
        knowledgeBaseId: 'kb-1',
      },
    ]);

    renderWithClient(<KnowledgeBasePage />);

    // mock t 恒等返回键名；banner 仅在 count>0 时渲染
    const banner = await screen.findByTestId('kb-uncategorized-banner');
    expect(banner).toHaveTextContent('kb.uncategorizedBanner');
    expect(screen.queryByText('未分类文档.pdf')).not.toBeInTheDocument();
  });
});
