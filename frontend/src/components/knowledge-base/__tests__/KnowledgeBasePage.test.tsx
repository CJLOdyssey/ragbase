import { listAssets } from '../../../api/client/assets';
import {
  createKnowledgeBase,
  listKnowledgeBases,
} from '../../../api/client/knowledgeBases';
import KnowledgeBasePage from '../KnowledgeBasePage';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
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

    const confirmButton = screen.getByRole('button', {
      name: 'confirm.confirm',
    });
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(createKnowledgeBase).toHaveBeenCalledWith('新知识库', '描述');
    });
  });

  it('shows uncategorized assets section', async () => {
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
    ]);

    renderWithClient(<KnowledgeBasePage />);

    await waitFor(() => {
      expect(screen.getByText('未分类文档.pdf')).toBeInTheDocument();
    });
  });
});
