import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import RetrievalLogPage from '../RetrievalLogPage';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { listRetrievalLogs } from '../../../api/client/retrievalLogs';

vi.mock('../../../api/client/retrievalLogs', () => ({
  listRetrievalLogs: vi.fn(),
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

describe('RetrievalLogPage', () => {
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
        {ui}
      </QueryClientProvider>
    );
  };

  it('renders retrieval log page title', async () => {
    vi.mocked(listRetrievalLogs).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    renderWithClient(<RetrievalLogPage />);
    
    await waitFor(() => {
      expect(screen.getByText('retrievalLogs.title')).toBeInTheDocument();
    });
  });

  it('displays filter controls', async () => {
    vi.mocked(listRetrievalLogs).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    renderWithClient(<RetrievalLogPage />);
    
    await waitFor(() => {
      expect(screen.getByText('retrievalLogs.emptyOnly')).toBeInTheDocument();
      expect(screen.getByText('retrievalLogs.maxLatency')).toBeInTheDocument();
    });
  });

  it('shows empty state when no logs', async () => {
    vi.mocked(listRetrievalLogs).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    renderWithClient(<RetrievalLogPage />);
    
    await waitFor(() => {
      expect(screen.getByText('retrievalLogs.noLogs')).toBeInTheDocument();
    });
  });

  it('renders log items', async () => {
    const mockLogs = {
      items: [
        {
          id: 'log-1',
          query: '测试查询',
          sources: [
            {
              id: 'source-1',
              content: '相关内容',
              score: 0.95,
              metadata: { title: '文档1' },
            },
          ],
          latency_ms: 150,
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    };

    vi.mocked(listRetrievalLogs).mockResolvedValue(mockLogs);

    renderWithClient(<RetrievalLogPage />);
    
    await waitFor(() => {
      expect(screen.getByText('测试查询')).toBeInTheDocument();
      expect(screen.getByText('150ms')).toBeInTheDocument();
    });
  });

  it('toggles empty only filter', async () => {
    vi.mocked(listRetrievalLogs).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    renderWithClient(<RetrievalLogPage />);
    
    await waitFor(() => {
      const checkbox = screen.getByRole('checkbox');
      fireEvent.click(checkbox);
    });

    await waitFor(() => {
      expect(listRetrievalLogs).toHaveBeenCalledWith(expect.objectContaining({
        empty_only: true,
      }));
    });
  });

  it('sets max latency filter', async () => {
    vi.mocked(listRetrievalLogs).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    renderWithClient(<RetrievalLogPage />);
    
    await waitFor(() => {
      const input = screen.getByPlaceholderText('0');
      fireEvent.change(input, { target: { value: '500' } });
    });

    await waitFor(() => {
      expect(listRetrievalLogs).toHaveBeenCalledWith(expect.objectContaining({
        max_latency_ms: 500,
      }));
    });
  });

  it('displays source details', async () => {
    const mockLogs = {
      items: [
        {
          id: 'log-1',
          query: '测试查询',
          sources: [
            {
              id: 'source-1',
              content: '相关内容1',
              score: 0.95,
              metadata: { title: '文档1' },
            },
            {
              id: 'source-2',
              content: '相关内容2',
              score: 0.85,
              metadata: { title: '文档2' },
            },
          ],
          latency_ms: 150,
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    };

    vi.mocked(listRetrievalLogs).mockResolvedValue(mockLogs);

    renderWithClient(<RetrievalLogPage />);
    
    await waitFor(() => {
      expect(screen.getByText('2 sources')).toBeInTheDocument();
    });
  });

  it('shows pagination when total > page_size', async () => {
    const mockLogs = {
      items: Array.from({ length: 20 }, (_, i) => ({
        id: `log-${i}`,
        query: `查询${i}`,
        sources: [],
        latency_ms: 100,
        created_at: '2024-01-01T00:00:00Z',
      })),
      total: 50,
      page: 1,
      page_size: 20,
    };

    vi.mocked(listRetrievalLogs).mockResolvedValue(mockLogs);

    renderWithClient(<RetrievalLogPage />);
    
    await waitFor(() => {
      expect(screen.getByText('common.prev')).toBeInTheDocument();
      expect(screen.getByText('common.next')).toBeInTheDocument();
    });
  });
});
