import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AdminUsersPage from '../AdminUsersPage';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { listAdminUsers, updateUserRole, updateUserStatus } from '../../../api/client/adminUsers';

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
      <QueryClientProvider client={queryClient}>
        {ui}
      </QueryClientProvider>
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
          user_id: 'user-1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'user',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
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

  it('shows role select for each user', async () => {
    const mockUsers = {
      users: [
        {
          user_id: 'user-1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'user',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    };

    vi.mocked(listAdminUsers).mockResolvedValue(mockUsers);

    renderWithClient(<AdminUsersPage />);
    
    await waitFor(() => {
      const roleSelect = screen.getByDisplayValue('user');
      expect(roleSelect).toBeInTheDocument();
    });
  });

  it('shows active status button', async () => {
    const mockUsers = {
      users: [
        {
          user_id: 'user-1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'user',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
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

  it('opens confirm dialog when changing role', async () => {
    const mockUsers = {
      users: [
        {
          user_id: 'user-1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'user',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    };

    vi.mocked(listAdminUsers).mockResolvedValue(mockUsers);

    renderWithClient(<AdminUsersPage />);
    
    await waitFor(() => {
      const roleSelect = screen.getByDisplayValue('user');
      fireEvent.change(roleSelect, { target: { value: 'admin' } });
    });

    await waitFor(() => {
      expect(screen.getByText('admin.users.confirmRoleChange')).toBeInTheDocument();
    });
  });

  it('opens confirm dialog when toggling status', async () => {
    const mockUsers = {
      users: [
        {
          user_id: 'user-1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'user',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    };

    vi.mocked(listAdminUsers).mockResolvedValue(mockUsers);

    renderWithClient(<AdminUsersPage />);
    
    await waitFor(() => {
      const statusButton = screen.getByText('admin.users.active');
      fireEvent.click(statusButton);
    });

    await waitFor(() => {
      expect(screen.getByText('admin.users.confirmStatusChange')).toBeInTheDocument();
    });
  });

  it('calls updateUserRole when confirming role change', async () => {
    const mockUsers = {
      users: [
        {
          user_id: 'user-1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'user',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
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
      const roleSelect = screen.getByDisplayValue('user');
      fireEvent.change(roleSelect, { target: { value: 'admin' } });
    });

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
          user_id: 'user-1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'user',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
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
      const statusButton = screen.getByText('admin.users.active');
      fireEvent.click(statusButton);
    });

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
        user_id: `user-${i}`,
        email: `user${i}@example.com`,
        name: `User ${i}`,
        role: 'user',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
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
