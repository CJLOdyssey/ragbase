import UserMenu from '../UserMenu';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string) => k,
    i18n: { language: 'zh-CN' },
  }),
}));

const { authMock } = vi.hoisted(() => ({
  authMock: {
    user: null,
    isAuthenticated: false,
    loading: false,
    logout: vi.fn(),
    openLoginModal: vi.fn(),
  },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => authMock,
}));

beforeEach(() => {
  authMock.user = null;
  authMock.isAuthenticated = false;
  authMock.loading = false;
});

function renderMenu(extra: Record<string, unknown> = {}) {
  return render(
    <UserMenu
      isUserMenuOpen
      setIsUserMenuOpen={vi.fn()}
      setIsSettingsOpen={vi.fn()}
      setIsApiOpen={vi.fn()}
      {...extra}
    />,
  );
}

describe('UserMenu', () => {
  it('renders nothing when closed', () => {
    render(
      <UserMenu
        isUserMenuOpen={false}
        setIsUserMenuOpen={vi.fn()}
        setIsSettingsOpen={vi.fn()}
        setIsApiOpen={vi.fn()}
      />,
    );
    expect(screen.queryByText('API')).not.toBeInTheDocument();
  });

  it('opens API management via menu item', () => {
    const setIsApiOpen = vi.fn();
    renderMenu({ setIsApiOpen });
    fireEvent.click(screen.getByText('API'));
    expect(setIsApiOpen).toHaveBeenCalledWith(true);
  });

  it('opens settings via menu item', () => {
    const setIsSettingsOpen = vi.fn();
    renderMenu({ setIsSettingsOpen });
    fireEvent.click(screen.getByText('sidebar.settings'));
    expect(setIsSettingsOpen).toHaveBeenCalledWith(true);
  });

  it('shows login action for guests and triggers login modal', () => {
    const setIsUserMenuOpen = vi.fn();
    renderMenu({ setIsUserMenuOpen });
    expect(screen.getByText('user.guest')).toBeInTheDocument();
    fireEvent.click(screen.getByText('user.loginRegister'));
    expect(authMock.openLoginModal).toHaveBeenCalled();
    expect(setIsUserMenuOpen).toHaveBeenCalledWith(false);
  });

  it('shows username and logout for authenticated users', () => {
    authMock.isAuthenticated = true;
    authMock.user = { username: 'alice', email: 'a@b.c' };
    const setIsUserMenuOpen = vi.fn();
    renderMenu({ setIsUserMenuOpen });
    expect(screen.getByText('alice')).toBeInTheDocument();
    fireEvent.click(screen.getByText('sidebar.logout'));
    expect(authMock.logout).toHaveBeenCalled();
  });

  it('shows online status text for authenticated users', () => {
    authMock.isAuthenticated = true;
    authMock.user = { username: 'alice', email: 'a@b.c' };
    renderMenu({});
    expect(screen.getByText('user.onlineStatus')).toBeInTheDocument();
  });

  it('shows loading skeletons while auth loading', () => {
    authMock.loading = true;
    authMock.isAuthenticated = true;
    renderMenu({});
    expect(screen.queryByText('user.guest')).not.toBeInTheDocument();
    expect(screen.queryByText('alice')).not.toBeInTheDocument();
  });

  it('closes on Escape keydown', () => {
    const setIsUserMenuOpen = vi.fn();
    renderMenu({ setIsUserMenuOpen });
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(setIsUserMenuOpen).toHaveBeenCalledWith(false);
  });

  it('toggles open state via the user button', () => {
    const setIsUserMenuOpen = vi.fn();
    render(
      <UserMenu
        isUserMenuOpen={false}
        setIsUserMenuOpen={setIsUserMenuOpen}
        setIsSettingsOpen={vi.fn()}
        setIsApiOpen={vi.fn()}
      />,
    );
    const btn = screen.getByRole('button', { name: /user.guest/ });
    fireEvent.click(btn);
    expect(setIsUserMenuOpen).toHaveBeenCalledWith(true);
  });

  it('closes the menu when already open', () => {
    const setIsUserMenuOpen = vi.fn();
    renderMenu({ setIsUserMenuOpen });
    fireEvent.click(screen.getByRole('button', { name: /user.guest/ }));
    expect(setIsUserMenuOpen).toHaveBeenCalledWith(false);
  });
});
