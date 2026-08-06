import * as authApi from '@/api/client/auth';
import { AuthProvider, useAuth } from '@/components/auth/AuthContext';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/client/auth', () => ({
  getAuthConfig: vi.fn(),
  getMe: vi.fn(),
  mergeGuestData: vi.fn().mockResolvedValue(undefined),
  refreshTokens: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
  verify: vi.fn(),
  forgotPassword: vi.fn(),
  resetPassword: vi.fn(),
  resendVerification: vi.fn(),
  sendRegisterCode: vi.fn(),
}));

vi.mock('@/api/client/instance', () => ({
  setTokens: vi.fn(),
  clearTokens: vi.fn(),
}));

function AuthProbe() {
  const { user, loading } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="user">{user ? user.email : 'null'}</span>
    </div>
  );
}

describe('AuthProvider', { tags: ['unit'] }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(authApi.getAuthConfig).mockReturnValue(new Promise(() => {}));
  });

  it('login() clears loading even when init() is still pending', async () => {
    function AuthProbeWithActions() {
      const { user, loading, login } = useAuth();
      return (
        <div>
          <span data-testid="loading">{String(loading)}</span>
          <span data-testid="user">{user ? user.email : 'null'}</span>
          <button onClick={() => void login('e2e@test.com', 'Test@1234')}>
            login
          </button>
        </div>
      );
    }

    vi.mocked(authApi.login).mockResolvedValue({
      access_token: 'at',
      refresh_token: 'rt',
      token_type: 'bearer',
      expires_in: 3600,
      user: {
        id: 'u1',
        email: 'e2e@test.com',
        username: 'e2e',
        roles: ['member'],
        is_verified: true,
      },
    });

    render(
      <AuthProvider>
        <AuthProbeWithActions />
      </AuthProvider>,
    );

    expect(screen.getByTestId('loading').textContent).toBe('true');

    await act(async () => {
      fireEvent.click(screen.getByText('login'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('e2e@test.com');
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });
  });

  it('register() clears loading even when init() is still pending', async () => {
    function AuthProbeWithActions() {
      const { user, loading, register } = useAuth();
      return (
        <div>
          <span data-testid="loading">{String(loading)}</span>
          <span data-testid="user">{user ? user.email : 'null'}</span>
          <button
            onClick={() => void register('new@test.com', '123456', 'Pass@123')}
          >
            register
          </button>
        </div>
      );
    }

    vi.mocked(authApi.register).mockResolvedValue({
      access_token: 'at',
      refresh_token: 'rt',
      token_type: 'bearer',
      expires_in: 3600,
      user: {
        id: 'u2',
        email: 'new@test.com',
        username: 'new',
        roles: ['member'],
        is_verified: true,
      },
    });

    render(
      <AuthProvider>
        <AuthProbeWithActions />
      </AuthProvider>,
    );

    expect(screen.getByTestId('loading').textContent).toBe('true');

    await act(async () => {
      fireEvent.click(screen.getByText('register'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('new@test.com');
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });
  });

  it('loading becomes false after init() completes when no refresh token exists', async () => {
    vi.mocked(authApi.getAuthConfig).mockResolvedValue({
      enabled: true,
      mode: 'jwt',
    });

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });
  });
});
