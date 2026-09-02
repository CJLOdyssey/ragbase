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

// setup.tsx globally mocks AuthContext for component tests; this suite tests
// the REAL provider, so unmock it (hoisted before the imports above run).
vi.unmock('@/components/auth/AuthContext');

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
  logout: vi.fn(),
}));

vi.mock('@/api/client/instance', () => ({}));

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
    // getMe 模拟 401 无 session 场景：reject 而非 resolve undefined
    // （真实 getMe 返回 UserResponse，不会 resolve undefined）
    vi.mocked(authApi.getMe).mockRejectedValue(new Error('Unauthorized'));
    vi.mocked(authApi.sendRegisterCode).mockResolvedValue({
      email_hint: 'a***@b.com',
    });
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

  it('loading becomes false after init() completes for a guest (no token state)', async () => {
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
    expect(authApi.getMe).toHaveBeenCalled();
  });

  it('restores a signed-in user via getMe (jwt mode) and clears loading', async () => {
    vi.mocked(authApi.getAuthConfig).mockResolvedValue({
      enabled: true,
      mode: 'jwt',
    });
    vi.mocked(authApi.getMe).mockResolvedValue({
      id: 'u1',
      email: 'user@test.com',
      username: 'user',
      roles: ['member'],
    });

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('user@test.com');
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });
    expect(localStorage.getItem('ragbase_user_id')).toBe('u1');
  });

  it('getMe failure falls back to refresh-then-restore', async () => {
    vi.mocked(authApi.getAuthConfig).mockResolvedValue({
      enabled: true,
      mode: 'jwt',
    });
    vi.mocked(authApi.getMe).mockRejectedValueOnce(new Error('expired'));
    vi.mocked(authApi.refreshTokens).mockResolvedValue(undefined);
    vi.mocked(authApi.getMe).mockResolvedValueOnce({
      id: 'u2',
      email: 'refreshed@test.com',
      username: 'r',
      roles: ['member'],
    });

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('refreshed@test.com');
    });
    expect(authApi.refreshTokens).toHaveBeenCalled();
  });

  it('logout clears state and reopens the login modal', async () => {
    vi.mocked(authApi.logout).mockResolvedValue(undefined);
    vi.mocked(authApi.getAuthConfig).mockReturnValue(new Promise(() => {}));

    function LogoutProbe() {
      const { user, login, logout, loginModalOpen } = useAuth();
      return (
        <div>
          <span data-testid="logged">{user ? user.email : 'null'}</span>
          <span data-testid="modal-open">{String(loginModalOpen)}</span>
          <button onClick={() => void login('e@e.com', 'P@ss1234')}>
            login
          </button>
          <button onClick={() => void logout()}>logout</button>
        </div>
      );
    }

    // 先通过 login 建立会话
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
        <LogoutProbe />
      </AuthProvider>,
    );
    await act(async () => {
      fireEvent.click(screen.getByText('login'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('logged').textContent).toBe('e2e@test.com');
    });

    await act(async () => {
      fireEvent.click(screen.getByText('logout'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('logged').textContent).toBe('null');
      expect(screen.getByTestId('modal-open').textContent).toBe('true');
    });
    expect(authApi.logout).toHaveBeenCalled();
  });

  it('logout API failure still clears local state', async () => {
    vi.mocked(authApi.logout).mockRejectedValue(new Error('net'));
    vi.mocked(authApi.getAuthConfig).mockReturnValue(new Promise(() => {}));
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

    function Probe() {
      const { user, login, logout } = useAuth();
      return (
        <div>
          <span data-testid="u">{user ? user.email : 'null'}</span>
          <button onClick={() => void login('e@e.com', 'P@ss1234')}>
            login
          </button>
          <button onClick={() => void logout()}>out</button>
        </div>
      );
    }
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await act(async () => {
      fireEvent.click(screen.getByText('login'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('u').textContent).toBe('e2e@test.com');
    });
    await act(async () => {
      fireEvent.click(screen.getByText('out'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('u').textContent).toBe('null');
    });
  });

  it('auth:unauthorized event logs the user out and opens the modal', async () => {
    vi.mocked(authApi.getAuthConfig).mockReturnValue(new Promise(() => {}));
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

    function Probe() {
      const { user, login, loginModalOpen } = useAuth();
      return (
        <div>
          <span data-testid="u">{user ? user.email : 'null'}</span>
          <span data-testid="open">{String(loginModalOpen)}</span>
          <button onClick={() => void login('e@e.com', 'P@ss1234')}>in</button>
        </div>
      );
    }
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await act(async () => {
      fireEvent.click(screen.getByText('in'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('u').textContent).toBe('e2e@test.com');
    });

    act(() => {
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('u').textContent).toBe('null');
      expect(screen.getByTestId('open').textContent).toBe('true');
    });
  });

  it('forgotPassword / resetPassword / verify / resendVerification delegate to the api', async () => {
    vi.mocked(authApi.getAuthConfig).mockReturnValue(new Promise(() => {}));
    vi.mocked(authApi.forgotPassword).mockResolvedValue(undefined);
    vi.mocked(authApi.resetPassword).mockResolvedValue(undefined);
    vi.mocked(authApi.verify).mockResolvedValue({
      access_token: 'at',
      refresh_token: 'rt',
      token_type: 'bearer',
      expires_in: 3600,
      user: {
        id: 'u1',
        email: 'v@test.com',
        username: 'v',
        roles: ['member'],
        is_verified: true,
      },
    });
    vi.mocked(authApi.resendVerification).mockResolvedValue(undefined);

    function Probe() {
      const {
        forgotPassword,
        resetPassword,
        verify,
        resendVerification,
        sendRegisterCode,
        openLoginModal,
        closeLoginModal,
        user,
      } = useAuth();
      return (
        <div>
          <span data-testid="u">{user ? user.email : 'null'}</span>
          <button onClick={() => void forgotPassword('a@b.com')}>fp</button>
          <button
            onClick={() => void resetPassword('a@b.com', '123456', 'X@y12345')}
          >
            rp
          </button>
          <button onClick={() => void verify('a@b.com', '123456')}>vf</button>
          <button onClick={() => void resendVerification('a@b.com')}>rv</button>
          <button onClick={() => void sendRegisterCode('a@b.com')}>sc</button>
          <button onClick={() => openLoginModal('register')}>om</button>
          <button onClick={() => closeLoginModal()}>cm</button>
        </div>
      );
    }

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await act(async () => {
      fireEvent.click(screen.getByText('fp'));
      fireEvent.click(screen.getByText('rp'));
      fireEvent.click(screen.getByText('vf'));
      fireEvent.click(screen.getByText('rv'));
      fireEvent.click(screen.getByText('sc'));
      fireEvent.click(screen.getByText('om'));
      fireEvent.click(screen.getByText('cm'));
    });

    expect(authApi.forgotPassword).toHaveBeenCalledWith('a@b.com');
    expect(authApi.resetPassword).toHaveBeenCalledWith(
      'a@b.com',
      '123456',
      'X@y12345',
    );
    expect(authApi.verify).toHaveBeenCalledWith('a@b.com', '123456');
    expect(authApi.resendVerification).toHaveBeenCalledWith('a@b.com');
    expect(authApi.sendRegisterCode).toHaveBeenCalledWith('a@b.com');
    await waitFor(() => {
      expect(screen.getByTestId('u').textContent).toBe('v@test.com');
    });
  });

  it('refresh failure does not re-dispatch auth:unauthorized (errors.ts owns it)', async () => {
    vi.useFakeTimers();
    try {
      vi.mocked(authApi.refreshTokens).mockRejectedValue({
        response: { status: 401 },
      });
      const dispatchSpy = vi.spyOn(window, 'dispatchEvent');

      render(
        <AuthProvider>
          <AuthProbe />
        </AuthProvider>,
      );

      // auth:login → 启动 10 分钟续期定时器
      act(() => {
        window.dispatchEvent(new Event('auth:login'));
      });
      await act(async () => {
        vi.advanceTimersByTime(10 * 60 * 1000);
        await Promise.resolve();
      });

      // 401/403 的登出 dispatch 已由 api/client/errors.ts normalizeError
      // 单点负责（instance.test.ts 覆盖）——AuthContext 不再重复触发，
      // 避免双发 auth:unauthorized。
      expect(
        dispatchSpy.mock.calls.some(
          (c) => (c[0] as Event).type === 'auth:unauthorized',
        ),
      ).toBe(false);
    } finally {
      vi.useRealTimers();
    }
  });
});
