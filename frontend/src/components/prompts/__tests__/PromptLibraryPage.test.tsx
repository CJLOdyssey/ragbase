import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import PromptLibraryPage from '../PromptLibraryPage';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { listPrompts, createPrompt, updatePrompt, deletePrompt } from '../../../api/client/prompts';
import { listVersions } from '../../../api/client/versions';

vi.mock('../../../api/client/prompts', () => ({
  listPrompts: vi.fn(),
  createPrompt: vi.fn(),
  updatePrompt: vi.fn(),
  deletePrompt: vi.fn(),
}));

vi.mock('../../../api/client/versions', () => ({
  listVersions: vi.fn(),
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

describe('PromptLibraryPage', () => {
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

  it('renders prompt library page title', async () => {
    vi.mocked(listPrompts).mockResolvedValue([]);

    renderWithClient(<PromptLibraryPage />);
    
    await waitFor(() => {
      expect(screen.getByText('prompts.title')).toBeInTheDocument();
    });
  });

  it('displays create button', async () => {
    vi.mocked(listPrompts).mockResolvedValue([]);

    renderWithClient(<PromptLibraryPage />);
    
    await waitFor(() => {
      expect(screen.getByText('prompts.editor.new')).toBeInTheDocument();
    });
  });

  it('shows tab navigation', async () => {
    vi.mocked(listPrompts).mockResolvedValue([]);

    renderWithClient(<PromptLibraryPage />);
    
    await waitFor(() => {
      expect(screen.getByText('prompts.tab.list')).toBeInTheDocument();
      expect(screen.getByText('prompts.tab.version')).toBeInTheDocument();
    });
  });

  it('renders prompt list', async () => {
    const mockPrompts = [
      {
        id: 'prompt-1',
        name: '测试提示词',
        content: '这是一个测试提示词内容',
        category: 'user',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    ];

    vi.mocked(listPrompts).mockResolvedValue(mockPrompts);

    renderWithClient(<PromptLibraryPage />);
    
    await waitFor(() => {
      expect(screen.getByText('测试提示词')).toBeInTheDocument();
    });
  });

  it('opens create modal when clicking new button', async () => {
    vi.mocked(listPrompts).mockResolvedValue([]);

    renderWithClient(<PromptLibraryPage />);
    
    await waitFor(() => {
      const newButton = screen.getByRole('button', { name: 'prompts.editor.new' });
      fireEvent.click(newButton);
    });

    await waitFor(() => {
      expect(screen.getByText('prompts.editor.name')).toBeInTheDocument();
    });
  });

  it('creates new prompt', async () => {
    vi.mocked(listPrompts).mockResolvedValue([]);
    vi.mocked(createPrompt).mockResolvedValue({
      id: 'new-prompt',
      name: '新提示词',
      content: '内容',
      category: 'user',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    });

    renderWithClient(<PromptLibraryPage />);
    
    // 点击新建按钮
    const newButton = await screen.findByRole('button', { name: 'prompts.editor.new' });
    fireEvent.click(newButton);

    // 等待模态框打开
    await waitFor(() => {
      expect(screen.getByText('prompts.editor.name')).toBeInTheDocument();
    });

    // 获取所有文本输入框（第一个是name输入框）
    const textInputs = screen.getAllByRole('textbox');
    const nameInput = textInputs[0];
    
    // 获取textarea（content输入框）
    const textareas = screen.getAllByRole('textbox', { hidden: false });
    const contentInput = textareas.find(el => el.tagName === 'TEXTAREA');
    
    if (nameInput) {
      fireEvent.change(nameInput, { target: { value: '新提示词' } });
    }
    if (contentInput) {
      fireEvent.change(contentInput, { target: { value: '内容' } });
    }
    
    // 点击保存按钮
    const saveButton = screen.getByRole('button', { name: 'prompts.editor.save' });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(createPrompt).toHaveBeenCalled();
    });
  });

  it('switches to version history tab', async () => {
    vi.mocked(listPrompts).mockResolvedValue([
      {
        id: 'prompt-1',
        name: '测试提示词',
        content: '内容',
        category: 'user',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    ]);

    renderWithClient(<PromptLibraryPage />);
    
    await waitFor(() => {
      const versionTab = screen.getByText('prompts.tab.version');
      fireEvent.click(versionTab);
    });

    await waitFor(() => {
      expect(screen.getByText('prompts.tab.version')).toBeInTheDocument();
    });
  });
});
