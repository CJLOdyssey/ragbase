import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

const mockUseAuth = vi.hoisted(() => vi.fn());

// Use correct relative path from __tests__/ to components/auth/
vi.mock('../../../auth', () => ({
  useAuth: (..._args: unknown[]) => mockUseAuth(..._args),
}));

import UserMenu from '../UserMenu';

describe('UserMenu', { tags: ['integration'] }, () => {
  const mockLogout = vi.fn();
  const mockOpenLoginModal = vi.fn();
  const mockSetIsUserMenuOpen = vi.fn();
  const mockSetIsSettingsOpen = vi.fn();
  const mockSetIsApiOpen = vi.fn();
  const mockOnOpenWorkstation = vi.fn();

  const authUnauthenticated = {
    user: null,
    isAuthenticated: false,
    logout: mockLogout,
    openLoginModal: mockOpenLoginModal,
  };

  const authAuthenticated = {
    user: { username: 'testuser', email: 'test@test.com' },
    isAuthenticated: true,
    logout: mockLogout,
    openLoginModal: mockOpenLoginModal,
  };

  const defaultProps = {
    isUserMenuOpen: true,
    setIsUserMenuOpen: mockSetIsUserMenuOpen,
    setIsSettingsOpen: mockSetIsSettingsOpen,
    setIsApiOpen: mockSetIsApiOpen,
    onOpenWorkstation: mockOnOpenWorkstation,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue(authUnauthenticated);
  });

  describe('unauthenticated', () => {
    it('renders menu items when open', () => {
      render(<UserMenu {...defaultProps} />);
      expect(screen.getByText('sidebar.workstation')).toBeInTheDocument();
      expect(screen.getByText('sidebar.settings')).toBeInTheDocument();
      expect(screen.getByText('sidebar.help')).toBeInTheDocument();
      expect(screen.getByText('API 管理')).toBeInTheDocument();
    });

    it('shows login button when not authenticated', () => {
      render(<UserMenu {...defaultProps} />);
      expect(screen.getByText('登录 / 注册')).toBeInTheDocument();
      expect(screen.queryByText('sidebar.logout')).not.toBeInTheDocument();
    });

    it('workstation is disabled when not authenticated', () => {
      render(<UserMenu {...defaultProps} />);
      expect(screen.getByText('sidebar.workstation').closest('button')).toBeDisabled();
    });

    it('shows guest name', () => {
      render(<UserMenu {...defaultProps} />);
      expect(screen.getByText('游客')).toBeInTheDocument();
    });

    it('shows offline status', () => {
      render(<UserMenu {...defaultProps} />);
      expect(screen.getByText('未登录')).toBeInTheDocument();
    });

    it('login button calls openLoginModal on click', () => {
      render(<UserMenu {...defaultProps} />);
      fireEvent.click(screen.getByText('登录 / 注册'));
      expect(mockOpenLoginModal).toHaveBeenCalled();
    });
  });

  describe('authenticated', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue(authAuthenticated);
    });

    it('shows username when authenticated', () => {
      render(<UserMenu {...defaultProps} />);
      expect(screen.getByText('testuser')).toBeInTheDocument();
    });

    it('shows logout when authenticated', () => {
      render(<UserMenu {...defaultProps} />);
      expect(screen.getByText('sidebar.logout')).toBeInTheDocument();
    });

    it('workstation is enabled when authenticated', () => {
      render(<UserMenu {...defaultProps} />);
      expect(screen.getByText('sidebar.workstation').closest('button')).not.toBeDisabled();
    });

    it('logout button calls logout on click', () => {
      render(<UserMenu {...defaultProps} />);
      fireEvent.click(screen.getByText('sidebar.logout'));
      expect(mockLogout).toHaveBeenCalled();
    });

    it('workstation button calls onOpenWorkstation', () => {
      render(<UserMenu {...defaultProps} />);
      fireEvent.click(screen.getByText('sidebar.workstation'));
      expect(mockOnOpenWorkstation).toHaveBeenCalled();
    });

    it('shows online status', () => {
      render(<UserMenu {...defaultProps} />);
      expect(screen.getByText('user.onlineStatus')).toBeInTheDocument();
    });
  });

  describe('interaction', () => {
    it('does not render when closed', () => {
      render(<UserMenu {...defaultProps} isUserMenuOpen={false} />);
      expect(screen.queryByText('API 管理')).not.toBeInTheDocument();
    });

    it('Escape key closes menu', () => {
      render(<UserMenu {...defaultProps} />);
      fireEvent.keyDown(document, { key: 'Escape' });
      expect(mockSetIsUserMenuOpen).toHaveBeenCalledWith(false);
    });

    it('Escape does not fire when menu closed', () => {
      render(<UserMenu {...defaultProps} isUserMenuOpen={false} />);
      fireEvent.keyDown(document, { key: 'Escape' });
      expect(mockSetIsUserMenuOpen).not.toHaveBeenCalled();
    });

    it('click outside closes menu', () => {
      render(<UserMenu {...defaultProps} />);
      fireEvent.mouseDown(document.body);
      expect(mockSetIsUserMenuOpen).toHaveBeenCalledWith(false);
    });

    it('click outside does not fire when menu closed', () => {
      render(<UserMenu {...defaultProps} isUserMenuOpen={false} />);
      fireEvent.mouseDown(document.body);
      expect(mockSetIsUserMenuOpen).not.toHaveBeenCalled();
    });

    it('trigger button opens menu when closed', () => {
      render(<UserMenu {...defaultProps} isUserMenuOpen={false} />);
      fireEvent.click(screen.getByText('游客').closest('button')!);
      expect(mockSetIsUserMenuOpen).toHaveBeenCalledWith(true);
    });

    it('trigger button closes menu when open', () => {
      render(<UserMenu {...defaultProps} />);
      const trigger = document.querySelector('[aria-haspopup="menu"]') as HTMLButtonElement;
      fireEvent.click(trigger);
      expect(mockSetIsUserMenuOpen).toHaveBeenCalledWith(false);
    });

    it('clicking API Key triggers setIsApiOpen', () => {
      render(<UserMenu {...defaultProps} />);
      fireEvent.click(screen.getByText('API 管理'));
      expect(mockSetIsApiOpen).toHaveBeenCalledWith(true);
    });

    it('clicking settings triggers setIsSettingsOpen', () => {
      render(<UserMenu {...defaultProps} />);
      fireEvent.click(screen.getByText('sidebar.settings'));
      expect(mockSetIsSettingsOpen).toHaveBeenCalledWith(true);
    });

    it('trigger has aria attributes', () => {
      render(<UserMenu {...defaultProps} />);
      const trigger = document.querySelector('[aria-haspopup="menu"]');
      expect(trigger?.getAttribute('aria-expanded')).toBe('true');
      expect(trigger?.getAttribute('aria-haspopup')).toBe('menu');
    });
  });
});
