import {
  listAdminUsers,
  updateUserRole,
  updateUserStatus,
} from '../../../api/client/adminUsers';
import AdminUsersPage from '../AdminUsersPage';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../../api/client/adminUsers', () => ({
  listAdminUsers: vi.fn(),
  updateUserRole: vi.fn(),
  updateUserStatus: vi.fn(),
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

vi.mock('../../../hooks/useMediaQuery', () => ({
  useIsMobile: () => true,
}));

describe('AdminUsersPage', () => {
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

  it('renders admin users page title', async () => {
    vi.mocked(listAdminUsers).mockResolvedValue({
      users: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    renderWithClient(<AdminUsersPage />);

    await waitFor(() => {
      expect(screen.getByText('admin.users.title')).toBeInTheDocument();
    });
  });

  it('displays search input', async () => {
    vi.mocked(listAdminUsers).mockResolvedValue({
      users: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    renderWithClient(<AdminUsersPage />);

    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText('admin.users.search');
      expect(searchInput).toBeInTheDocument();
    });
  });

  it('shows empty state when no users', async () => {
    vi.mocked(listAdminUsers).mockResolvedValue({
      users: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    renderWithClient(<AdminUsersPage />);

    await waitFor(() => {
      expect(screen.getByText('admin.users.noUsers')).toBeInTheDocument();
    });
  });

  it('renders user list', async () => {
    const mockUsers = {
      users: [
        {
          userId: 'user-1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'member',
          isActive: true,
          createdAt: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    };

    vi.mocked(listAdminUsers).mockResolvedValue(mockUsers);

    renderWithClient(<AdminUsersPage />);

    await waitFor(() => {
      expect(screen.getByText('Test User')).toBeInTheDocument();
      expect(screen.getByText('test@example.com')).toBeInTheDocument();
    });
  });

  it('updates search query', async () => {
    vi.mocked(listAdminUsers).mockResolvedValue({
      users: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    renderWithClient(<AdminUsersPage />);

    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText('admin.users.search');
      fireEvent.change(searchInput, { target: { value: 'test' } });
      expect(searchInput).toHaveValue('test');
    });
  });

  /**
   * Opens the per-row "more actions" ActionSheet (renders inside antd Modal)
   * and clicks a menu item by i18n key.
   */
  const openRowMenuAndClick = async (itemText: string) => {
    const moreButton = screen.getByRole('button', {
      name: 'admin.users.moreActions',
    });
    fireEvent.click(moreButton);
    const menu = await waitFor(() => {
      // ActionSheet renders buttons inside antd Modal body
      const buttons = screen.getAllByRole('button');
      const item = buttons.find((b) => b.textContent?.trim() === itemText);
      expect(item).toBeDefined();
      return item as HTMLElement;
    });
    fireEvent.click(menu);
  };

  it('offers role editing in the row actions menu', async () => {
    const mockUsers = {
      users: [
        {
          userId: 'user-1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'member',
          isActive: true,
          createdAt: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    };

    vi.mocked(listAdminUsers).mockResolvedValue(mockUsers);

    renderWithClient(<AdminUsersPage />);

    await waitFor(() => {
      expect(screen.getByText('Test User')).toBeInTheDocument();
    });
    await openRowMenuAndClick('admin.users.role');

    // Role edit opens the confirm dialog with the toggled target role.
    await waitFor(() => {
      expect(
        screen.getByText('admin.users.confirmRoleChange'),
      ).toBeInTheDocument();
    });
  });

  it('shows active status button', async () => {
    const mockUsers = {
      users: [
        {
          userId: 'user-1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'member',
          isActive: true,
          createdAt: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    };

    vi.mocked(listAdminUsers).mockResolvedValue(mockUsers);

    renderWithClient(<AdminUsersPage />);

    await waitFor(() => {
      expect(screen.getByText('admin.users.active')).toBeInTheDocument();
    });
  });

  it('opens confirm dialog when changing role via actions menu', async () => {
    const mockUsers = {
      users: [
        {
          userId: 'user-1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'member',
          isActive: true,
          createdAt: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    };

    vi.mocked(listAdminUsers).mockResolvedValue(mockUsers);

    renderWithClient(<AdminUsersPage />);

    await waitFor(() => {
      expect(screen.getByText('Test User')).toBeInTheDocument();
    });
    await openRowMenuAndClick('admin.users.role');

    await waitFor(() => {
      expect(
        screen.getByText('admin.users.confirmRoleChange'),
      ).toBeInTheDocument();
    });
  });

  it('opens confirm dialog when toggling status via actions menu', async () => {
    const mockUsers = {
      users: [
        {
          userId: 'user-1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'member',
          isActive: true,
          createdAt: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    };

    vi.mocked(listAdminUsers).mockResolvedValue(mockUsers);

    renderWithClient(<AdminUsersPage />);

    await waitFor(() => {
      expect(screen.getByText('Test User')).toBeInTheDocument();
    });
    await openRowMenuAndClick('admin.users.disable');

    await waitFor(() => {
      expect(
        screen.getByText('admin.users.confirmStatusChange'),
      ).toBeInTheDocument();
    });
  });

  it('calls updateUserRole when confirming role change', async () => {
    const mockUsers = {
      users: [
        {
          userId: 'user-1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'member',
          isActive: true,
          createdAt: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    };

    vi.mocked(listAdminUsers).mockResolvedValue(mockUsers);
    vi.mocked(updateUserRole).mockResolvedValue(undefined);

    renderWithClient(<AdminUsersPage />);

    await waitFor(() => {
      expect(screen.getByText('Test User')).toBeInTheDocument();
    });
    await openRowMenuAndClick('admin.users.role');

    await waitFor(() => {
      const confirmButton = screen.getByText('confirm.confirm');
      fireEvent.click(confirmButton);
    });

    await waitFor(() => {
      expect(updateUserRole).toHaveBeenCalledWith('user-1', 'admin');
    });
  });

  it('calls updateUserStatus when confirming status change', async () => {
    const mockUsers = {
      users: [
        {
          userId: 'user-1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'member',
          isActive: true,
          createdAt: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    };

    vi.mocked(listAdminUsers).mockResolvedValue(mockUsers);
    vi.mocked(updateUserStatus).mockResolvedValue(undefined);

    renderWithClient(<AdminUsersPage />);

    await waitFor(() => {
      expect(screen.getByText('Test User')).toBeInTheDocument();
    });
    await openRowMenuAndClick('admin.users.disable');

    await waitFor(() => {
      const confirmButton = screen.getByText('confirm.confirm');
      fireEvent.click(confirmButton);
    });

    await waitFor(() => {
      expect(updateUserStatus).toHaveBeenCalledWith('user-1', false);
    });
  });

  it('shows pagination when total > page_size', async () => {
    const mockUsers = {
      users: Array.from({ length: 20 }, (_, i) => ({
        userId: `user-${i}`,
        email: `user${i}@example.com`,
        name: `User ${i}`,
        role: 'member',
        isActive: true,
        createdAt: '2024-01-01T00:00:00Z',
      })),
      total: 50,
      page: 1,
      page_size: 20,
    };

    vi.mocked(listAdminUsers).mockResolvedValue(mockUsers);

    renderWithClient(<AdminUsersPage />);

    await waitFor(() => {
      expect(screen.getByText('common.prev')).toBeInTheDocument();
      expect(screen.getByText('common.next')).toBeInTheDocument();
    });
  });
});
