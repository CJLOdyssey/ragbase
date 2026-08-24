import {
  createPrompt,
  listPrompts,
  updatePrompt,
} from '../../../api/client/prompts';
import { listVersions } from '../../../api/client/versions';
import PromptLibraryPage from '../PromptLibraryPage';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

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
        <MemoryRouter>{ui}</MemoryRouter>
      </QueryClientProvider>,
    );
  };

  const mockPrompt = {
    id: 'prompt-1',
    name: '测试提示词',
    description: '测试描述',
    content: '内容',
    category: 'user',
    model: null,
    status: 'active',
    version: 'v1',
    created_at: '2024-01-01T00:00:00Z',
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

  it('shows table headers', async () => {
    vi.mocked(listPrompts).mockResolvedValue([
      {
        id: 'prompt-1',
        name: '测试提示词',
        description: '测试描述',
        content: '内容',
        category: 'user',
        model: null,
        status: 'active',
        version: 'v1',
        created_at: '2024-01-01T00:00:00Z',
      },
    ]);

    renderWithClient(<PromptLibraryPage />);

    await waitFor(() => {
      expect(screen.getByText('prompts.table.name')).toBeInTheDocument();
      expect(screen.getByText('prompts.table.desc')).toBeInTheDocument();
      expect(screen.getByText('prompts.table.status')).toBeInTheDocument();
      expect(screen.getByText('prompts.table.version')).toBeInTheDocument();
      expect(screen.getByText('prompts.table.uses')).toBeInTheDocument();
      expect(screen.getByText('prompts.table.actions')).toBeInTheDocument();
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
      const newButton = screen.getByRole('button', {
        name: 'prompts.editor.new',
      });
      fireEvent.click(newButton);
    });

    await waitFor(() => {
      // Modal title + button both have this text
      expect(
        screen.getAllByText('prompts.editor.new').length,
      ).toBeGreaterThanOrEqual(2);
    });
  });

  it('creates new prompt', async () => {
    vi.mocked(listPrompts).mockResolvedValue([]);
    vi.mocked(createPrompt).mockResolvedValue({
      id: 'new-prompt',
      name: '新提示词',
      description: null,
      content: '内容',
      category: 'user',
      model: null,
      status: 'active',
      version: 'v1',
      created_at: '2024-01-01T00:00:00Z',
    });

    renderWithClient(<PromptLibraryPage />);

    // 点击新建按钮
    const newButton = await screen.findByRole('button', {
      name: 'prompts.editor.new',
    });
    fireEvent.click(newButton);

    // 等待模态框打开 — 检查取消按钮出现
    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'confirm.cancel' }),
      ).toBeInTheDocument();
    });

    // 获取所有文本输入框（第一个是name输入框）
    const textInputs = screen.getAllByRole('textbox');
    const nameInput = textInputs[0];

    // 获取textarea（content输入框）
    const textareas = screen.getAllByRole('textbox', { hidden: false });
    const contentInput = textareas.find((el) => el.tagName === 'TEXTAREA');

    if (nameInput) {
      fireEvent.change(nameInput, { target: { value: '新提示词' } });
    }
    if (contentInput) {
      fireEvent.change(contentInput, { target: { value: '内容' } });
    }

    // 点击保存按钮
    const saveButton = screen.getByRole('button', {
      name: 'prompts.editor.save',
    });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(createPrompt).toHaveBeenCalled();
    });
  });

  it('renders prompt rows in table', async () => {
    vi.mocked(listPrompts).mockResolvedValue([
      {
        id: 'prompt-1',
        name: '测试提示词',
        description: '测试描述',
        content: '内容',
        category: 'user',
        model: null,
        status: 'active',
        version: 'v1',
        created_at: '2024-01-01T00:00:00Z',
      },
    ]);

    renderWithClient(<PromptLibraryPage />);

    await waitFor(() => {
      expect(screen.getByText('测试提示词')).toBeInTheDocument();
      expect(screen.getByText('测试描述')).toBeInTheDocument();
      expect(screen.getByText('v1')).toBeInTheDocument();
    });
  });

  it('opens detail modal on row click and opens editor via its edit button', async () => {
    vi.mocked(listPrompts).mockResolvedValue([mockPrompt]);

    renderWithClient(<PromptLibraryPage />);

    fireEvent.click(await screen.findByText('测试提示词'));

    // antd 用 aria-labelledby 指向标题容器，可访问名为「名称+徽标+版本」拼接，用包含式匹配
    const detailDialog = await screen.findByRole('dialog', {
      name: /测试提示词/,
    });
    expect(
      within(detailDialog).getByText('prompts.detail.basicInfo'),
    ).toBeInTheDocument();

    fireEvent.click(
      within(detailDialog).getByRole('button', { name: 'prompts.list.edit' }),
    );

    await waitFor(() => {
      expect(screen.getByText('prompts.editor.edit')).toBeInTheDocument();
    });
    const nameInput = screen.getByPlaceholderText('如：产品问答助手');
    expect(nameInput).toHaveValue('测试提示词');
  });

  it('rolls back to a historical version from the history modal', async () => {
    vi.mocked(listPrompts).mockResolvedValue([
      {
        id: 'prompt-1',
        name: '测试提示词',
        description: '测试描述',
        content: '当前内容',
        category: 'user',
        model: null,
        status: 'active',
        version: 'v2',
        created_at: '2024-01-01T00:00:00Z',
      },
    ]);
    vi.mocked(listVersions).mockResolvedValue([
      {
        id: 'version-1',
        version_num: 1,
        resource_type: 'prompt',
        resource_id: 'prompt-1',
        snapshot: {
          name: '历史名称',
          category: 'system',
          content: '历史内容',
        },
        created_at: '2024-01-01T00:00:00Z',
        created_by: 'user1',
      },
    ]);
    vi.mocked(updatePrompt).mockResolvedValue({
      id: 'prompt-1',
      name: '历史名称',
      description: null,
      content: '历史内容',
      category: 'system',
      model: null,
      status: 'active',
      version: 'v3',
      created_at: '2024-01-01T00:00:00Z',
    });

    renderWithClient(<PromptLibraryPage />);

    const historyButton = await screen.findByRole('button', {
      name: 'prompts.list.history',
    });
    fireEvent.click(historyButton);

    await waitFor(() => {
      expect(screen.getByText('prompts.history.title')).toBeInTheDocument();
    });

    const rollbackButton = await screen.findByRole('button', {
      name: 'prompts.version.rollback',
    });
    fireEvent.click(rollbackButton);

    await waitFor(() => {
      expect(updatePrompt).toHaveBeenCalledWith('prompt-1', {
        name: '历史名称',
        category: 'system',
        content: '历史内容',
      });
    });
  });
});
