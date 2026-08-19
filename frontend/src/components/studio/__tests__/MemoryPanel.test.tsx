import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import MemoryPanel from '../MemoryPanel';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { listSessionMemories, deleteMemory, exportSessionMemories } from '../../../api/client/sessions';

vi.mock('../../../api/client/sessions', () => ({
  listSessionMemories: vi.fn(),
  deleteMemory: vi.fn(),
  exportSessionMemories: vi.fn(),
}));

vi.mock('../../../utils/useToast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
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

describe('MemoryPanel', () => {
  let queryClient: QueryClient;
  const mockSessionId = 'session-1';
  const mockOnClose = vi.fn();

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

  it('renders memory panel title', async () => {
    vi.mocked(listSessionMemories).mockResolvedValue([]);

    renderWithClient(<MemoryPanel sessionId={mockSessionId} onClose={mockOnClose} />);
    
    await waitFor(() => {
      expect(screen.getByText('memory.title')).toBeInTheDocument();
    });
  });

  it('displays export button', async () => {
    vi.mocked(listSessionMemories).mockResolvedValue([]);

    renderWithClient(<MemoryPanel sessionId={mockSessionId} onClose={mockOnClose} />);
    
    await waitFor(() => {
      const exportButton = screen.getByTitle('memory.exportJson');
      expect(exportButton).toBeInTheDocument();
    });
  });

  it('displays close button', async () => {
    vi.mocked(listSessionMemories).mockResolvedValue([]);

    renderWithClient(<MemoryPanel sessionId={mockSessionId} onClose={mockOnClose} />);
    
    await waitFor(() => {
      const closeButton = screen.getByTitle('confirm.close');
      expect(closeButton).toBeInTheDocument();
    });
  });

  it('calls onClose when close button is clicked', async () => {
    vi.mocked(listSessionMemories).mockResolvedValue([]);

    renderWithClient(<MemoryPanel sessionId={mockSessionId} onClose={mockOnClose} />);
    
    await waitFor(() => {
      const closeButton = screen.getByTitle('confirm.close');
      fireEvent.click(closeButton);
    });

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('shows loading state', async () => {
    vi.mocked(listSessionMemories).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    renderWithClient(<MemoryPanel sessionId={mockSessionId} onClose={mockOnClose} />);
    
    await waitFor(() => {
      expect(screen.getByText('common.loading')).toBeInTheDocument();
    });
  });

  it('shows empty state when no memories', async () => {
    vi.mocked(listSessionMemories).mockResolvedValue([]);

    renderWithClient(<MemoryPanel sessionId={mockSessionId} onClose={mockOnClose} />);
    
    await waitFor(() => {
      expect(screen.getByText('memory.empty')).toBeInTheDocument();
      expect(screen.getByText('memory.emptyDesc')).toBeInTheDocument();
    });
  });

  it('renders memory list', async () => {
    const mockMemories = [
      {
        id: 'memory-1',
        agent_role: 'assistant',
        content_type: 'text',
        summary: 'Test memory summary',
        created_at: '2024-01-01T00:00:00Z',
      },
    ];

    vi.mocked(listSessionMemories).mockResolvedValue(mockMemories);

    renderWithClient(<MemoryPanel sessionId={mockSessionId} onClose={mockOnClose} />);
    
    await waitFor(() => {
      expect(screen.getByText('Test memory summary')).toBeInTheDocument();
      expect(screen.getByText('assistant')).toBeInTheDocument();
      expect(screen.getByText('text')).toBeInTheDocument();
    });
  });

  it('displays delete button for each memory', async () => {
    const mockMemories = [
      {
        id: 'memory-1',
        agent_role: 'assistant',
        content_type: 'text',
        summary: 'Test memory summary',
        created_at: '2024-01-01T00:00:00Z',
      },
    ];

    vi.mocked(listSessionMemories).mockResolvedValue(mockMemories);

    renderWithClient(<MemoryPanel sessionId={mockSessionId} onClose={mockOnClose} />);
    
    await waitFor(() => {
      const deleteButton = screen.getByTitle('confirm.delete');
      expect(deleteButton).toBeInTheDocument();
    });
  });

  it('opens confirm dialog when delete button is clicked', async () => {
    const mockMemories = [
      {
        id: 'memory-1',
        agent_role: 'assistant',
        content_type: 'text',
        summary: 'Test memory summary',
        created_at: '2024-01-01T00:00:00Z',
      },
    ];

    vi.mocked(listSessionMemories).mockResolvedValue(mockMemories);

    renderWithClient(<MemoryPanel sessionId={mockSessionId} onClose={mockOnClose} />);
    
    await waitFor(() => {
      const deleteButton = screen.getByTitle('confirm.delete');
      fireEvent.click(deleteButton);
    });

    await waitFor(() => {
      expect(screen.getByText('memory.deleteTitle')).toBeInTheDocument();
      expect(screen.getByText('memory.deleteConfirm')).toBeInTheDocument();
    });
  });

  it('calls deleteMemory when confirming deletion', async () => {
    const mockMemories = [
      {
        id: 'memory-1',
        agent_role: 'assistant',
        content_type: 'text',
        summary: 'Test memory summary',
        created_at: '2024-01-01T00:00:00Z',
      },
    ];

    vi.mocked(listSessionMemories).mockResolvedValue(mockMemories);
    vi.mocked(deleteMemory).mockResolvedValue(undefined);

    renderWithClient(<MemoryPanel sessionId={mockSessionId} onClose={mockOnClose} />);
    
    await waitFor(() => {
      const deleteButton = screen.getByTitle('confirm.delete');
      fireEvent.click(deleteButton);
    });

    await waitFor(() => {
      const confirmButton = screen.getByText('confirm.delete');
      fireEvent.click(confirmButton);
    });

    await waitFor(() => {
      expect(deleteMemory).toHaveBeenCalledWith('memory-1', expect.anything());
    });
  });

  it('calls exportSessionMemories when export button is clicked', async () => {
    vi.mocked(listSessionMemories).mockResolvedValue([]);
    vi.mocked(exportSessionMemories).mockResolvedValue(new Blob());

    renderWithClient(<MemoryPanel sessionId={mockSessionId} onClose={mockOnClose} />);
    
    await waitFor(() => {
      const exportButton = screen.getByTitle('memory.exportJson');
      fireEvent.click(exportButton);
    });

    await waitFor(() => {
      expect(exportSessionMemories).toHaveBeenCalledWith(mockSessionId, 'json');
    });
  });

  it('displays created_at date when available', async () => {
    const mockMemories = [
      {
        id: 'memory-1',
        agent_role: 'assistant',
        content_type: 'text',
        summary: 'Test memory summary',
        created_at: '2024-01-01T00:00:00Z',
      },
    ];

    vi.mocked(listSessionMemories).mockResolvedValue(mockMemories);

    renderWithClient(<MemoryPanel sessionId={mockSessionId} onClose={mockOnClose} />);
    
    await waitFor(() => {
      // Check if date is displayed (format may vary by locale)
      expect(screen.getByText(/1\/1\/2024/)).toBeInTheDocument();
    });
  });
});
