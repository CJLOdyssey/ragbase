import { useAuth } from '../AuthContext';
import LoginTrigger from '../LoginTrigger';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

vi.mock('../AuthContext', () => ({
  useAuth: vi.fn(),
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

const mockUseAuth = vi.mocked(useAuth);

describe('LoginTrigger', { tags: ['unit'] }, () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
      openLoginModal: vi.fn(),
      logout: vi.fn(),
    } as ReturnType<typeof useAuth>);
  });

  it('shows login/register buttons when anonymous', () => {
    render(
      <MemoryRouter>
        <LoginTrigger />
      </MemoryRouter>,
    );
    expect(screen.getByText('auth.login')).toBeTruthy();
    expect(screen.getByText('auth.register')).toBeTruthy();
  });

  it('opens login modal on click', () => {
    const openLoginModal = vi.fn();
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
      openLoginModal,
      logout: vi.fn(),
    } as ReturnType<typeof useAuth>);
    render(
      <MemoryRouter>
        <LoginTrigger />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('auth.login'));
    expect(openLoginModal).toHaveBeenCalledWith('login');
    fireEvent.click(screen.getByText('auth.register'));
    expect(openLoginModal).toHaveBeenCalledWith('register');
  });

  it('shows username and logout when authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: { username: '测试用户', email: 'a@b.co' },
      openLoginModal: vi.fn(),
      logout: vi.fn(),
    } as unknown as ReturnType<typeof useAuth>);
    render(
      <MemoryRouter>
        <LoginTrigger />
      </MemoryRouter>,
    );
    expect(screen.getByText('测试用户')).toBeTruthy();
    expect(screen.getByText('auth.logout')).toBeTruthy();
  });

  it('has no axe violations', async () => {
    const { container } = render(
      <MemoryRouter>
        <LoginTrigger />
      </MemoryRouter>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
