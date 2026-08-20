import { testRetrieval } from '../../../api/client/ragTest';
import RetrievalTestModal from '../RetrievalTestModal';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

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

describe('RetrievalTestModal', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.clearAllMocks();
  });

  const renderModal = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <RetrievalTestModal
          knowledgeBaseId="kb-1"
          knowledgeBaseName="产品知识库"
          onClose={vi.fn()}
        />
      </QueryClientProvider>,
    );

  it('renders title with kb name', () => {
    renderModal();
    expect(screen.getByText('ragTest.title · 产品知识库')).toBeInTheDocument();
  });

  it('runs test and shows hit sources', async () => {
    vi.mocked(testRetrieval).mockResolvedValue({
      originalQuery: '部署方式',
      query: '部署方式',
      hitCount: 1,
      embeddingConfigured: true,
      sources: [
        {
          assetId: 'asset-1',
          assetName: '产品手册.pdf',
          text: '支持私有化部署',
          similarity: 0.72,
        },
      ],
    });

    renderModal();

    const input = screen.getByPlaceholderText('ragTest.queryPlaceholder');
    fireEvent.change(input, { target: { value: '部署方式' } });

    const runButton = screen.getByRole('button', { name: 'ragTest.run' });
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(testRetrieval).toHaveBeenCalledWith(
        {
          query: '部署方式',
          topK: 5,
          rewrite: false,
          knowledgeBaseId: 'kb-1',
        },
        expect.anything(),
      );
    });
    await waitFor(() => {
      expect(screen.getByText('产品手册.pdf')).toBeInTheDocument();
      expect(screen.getByText('支持私有化部署')).toBeInTheDocument();
    });
  });

  it('shows empty state on zero hits', async () => {
    vi.mocked(testRetrieval).mockResolvedValue({
      originalQuery: '无匹配问题',
      query: '无匹配问题',
      hitCount: 0,
      embeddingConfigured: true,
      sources: [],
    });

    renderModal();

    const input = screen.getByPlaceholderText('ragTest.queryPlaceholder');
    fireEvent.change(input, { target: { value: '无匹配问题' } });
    fireEvent.click(screen.getByRole('button', { name: 'ragTest.run' }));

    await waitFor(() => {
      expect(screen.getByText('ragTest.noHits')).toBeInTheDocument();
    });
  });

  it('disables run button when query empty', () => {
    renderModal();
    const runButton = screen.getByRole('button', { name: 'ragTest.run' });
    expect(runButton).toBeDisabled();
  });
});
