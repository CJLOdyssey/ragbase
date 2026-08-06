import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const mockAxiosInstance = {
  interceptors: {
    request: { use: vi.fn() },
    response: { use: vi.fn() },
  },
};

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
  AxiosError: class AxiosError extends Error {
    code?: string;
    config?: Record<string, unknown>;
    response?: { status: number; data: unknown; headers: Record<string, string> };
    constructor(message: string, code?: string, response?: { status: number; data: unknown; headers: Record<string, string> }, config?: Record<string, unknown>) {
      super(message);
      this.name = 'AxiosError';
      this.code = code;
      this.response = response;
      this.config = config;
    }
  },
}));

vi.mock('./errors', () => ({
  normalizeError: vi.fn((err: unknown) => {
    throw err;
  }),
}));

vi.mock('../auth', () => ({
  refreshTokens: vi.fn(),
}));

vi.mock('../../utils/logger', () => ({
  default: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
}));

const REFRESH_KEY = 'agentstudio_refresh_token';

describe('instance', { tags: ['unit'] }, () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    localStorage.clear();
    mockAxiosInstance.interceptors.request.use.mockClear();
    mockAxiosInstance.interceptors.response.use.mockClear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe('setTokens', () => {
    it('ignores access parameter and stores refresh token', async () => {
      const { setTokens } = await import('../instance');
      setTokens('some-access', 'refresh-456');

      expect(localStorage.getItem(REFRESH_KEY)).toBe('refresh-456');
    });

    it('removes refresh token when null is passed', async () => {
      localStorage.setItem(REFRESH_KEY, 'old-refresh');

      const { setTokens } = await import('../instance');
      setTokens(null, null);

      expect(localStorage.getItem(REFRESH_KEY)).toBeNull();
    });

    it('only stores refresh token when passed', async () => {
      const { setTokens } = await import('../instance');
      setTokens(null, 'refresh-only');

      expect(localStorage.getItem(REFRESH_KEY)).toBe('refresh-only');
    });
  });

  describe('getAccessToken', () => {
    it('returns null (access token is httpOnly cookie)', async () => {
      const { getAccessToken } = await import('../instance');
      expect(getAccessToken()).toBeNull();
    });
  });

  describe('clearTokens', () => {
    it('removes refresh token', async () => {
      localStorage.setItem(REFRESH_KEY, 'refresh');

      const { clearTokens } = await import('../instance');
      clearTokens();

      expect(localStorage.getItem(REFRESH_KEY)).toBeNull();
    });
  });

  describe('request interceptor', () => {
    it('does not add Authorization header (access token is httpOnly cookie)', async () => {
      let capturedInterceptor: ((config: Record<string, unknown>) => Record<string, unknown>) | null = null;
      mockAxiosInstance.interceptors.request.use.mockImplementation((fn: (config: Record<string, unknown>) => Record<string, unknown>) => {
        capturedInterceptor = fn;
      });

      await import('../instance');

      const config = { headers: {} as Record<string, string> };
      const result = capturedInterceptor!(config);

      expect(result.headers.Authorization).toBeUndefined();
    });

    it('adds X-User-ID header', async () => {
      let capturedInterceptor: ((config: Record<string, unknown>) => Record<string, unknown>) | null = null;
      mockAxiosInstance.interceptors.request.use.mockImplementation((fn: (config: Record<string, unknown>) => Record<string, unknown>) => {
        capturedInterceptor = fn;
      });

      await import('../instance');

      const config = { headers: {} as Record<string, string>, method: 'GET', url: '/test' };
      const result = capturedInterceptor!(config);

      expect(result.headers['X-User-ID']).toBeDefined();
    });

    it('generates user ID when none exists', async () => {
      let capturedInterceptor: ((config: Record<string, unknown>) => Record<string, unknown>) | null = null;
      mockAxiosInstance.interceptors.request.use.mockImplementation((fn: (config: Record<string, unknown>) => Record<string, unknown>) => {
        capturedInterceptor = fn;
      });

      await import('../instance');

      const config = { headers: {} as Record<string, string>, method: 'GET', url: '/test' };
      const result = capturedInterceptor!(config);

      const uid = result.headers['X-User-ID'] as string;
      expect(uid).toBeDefined();
      expect(uid.startsWith('u_')).toBe(true);
      expect(localStorage.getItem('agentstudio_user_id')).toBe(uid);
    });

    it('reuses existing user ID', async () => {
      localStorage.setItem('agentstudio_user_id', 'existing-uid');

      let capturedInterceptor: ((config: Record<string, unknown>) => Record<string, unknown>) | null = null;
      mockAxiosInstance.interceptors.request.use.mockImplementation((fn: (config: Record<string, unknown>) => Record<string, unknown>) => {
        capturedInterceptor = fn;
      });

      await import('../instance');

      const config = { headers: {} as Record<string, string> };
      const result = capturedInterceptor!(config);

      expect(result.headers['X-User-ID']).toBe('existing-uid');
    });
  });

  describe('response interceptor', () => {
    it('returns successful response as-is', async () => {
      let successHandler: ((response: unknown) => unknown) | null = null;
      mockAxiosInstance.interceptors.response.use.mockImplementation((s: (response: unknown) => unknown) => {
        successHandler = s;
      });

      await import('../instance');

      const response = {
        config: { method: 'GET', url: '/test' },
        status: 200,
        data: { ok: true },
      };

      const result = successHandler!(response);
      expect(result).toBe(response);
    });

    it('rejects non-401 errors', async () => {
      let errorHandler: ((error: unknown) => Promise<unknown>) | null = null;
      mockAxiosInstance.interceptors.response.use.mockImplementation(
        (_s: (response: unknown) => unknown, e: (error: unknown) => Promise<unknown>) => {
          errorHandler = e;
        },
      );

      await import('../instance');

      const axiosErr = new (await import('axios')).AxiosError(
        'Not Found',
      ) as Error & { code?: string; config?: { method: string; url: string; _retry?: boolean }; response?: { status: number; data: unknown; headers: Record<string, string> } };
      (axiosErr as Record<string, unknown>).code = 'ERR_BAD_REQUEST';
      (axiosErr as Record<string, unknown>).config = { method: 'GET', url: '/missing', _retry: false };
      (axiosErr as Record<string, unknown>).response = { status: 404, data: { detail: 'Not Found' }, headers: {} };

      try {
        await errorHandler!(axiosErr);
        expect.fail('Should have thrown');
      } catch (e) {
        expect(e).toBeDefined();
      }
    });

    it('rejects 401 errors when no refresh token', async () => {
      let errorHandler: ((error: unknown) => Promise<unknown>) | null = null;
      mockAxiosInstance.interceptors.response.use.mockImplementation(
        (_s: (response: unknown) => unknown, e: (error: unknown) => Promise<unknown>) => {
          errorHandler = e;
        },
      );

      localStorage.removeItem(REFRESH_KEY);
      const authSpy = vi.fn();
      window.addEventListener('auth:unauthorized', authSpy);

      await import('../instance');

      const axiosErr = new (await import('axios')).AxiosError(
        'Unauthorized',
      ) as Error & { code?: string; config?: { method: string; url: string; _retry?: boolean }; response?: { status: number; data: unknown; headers: Record<string, string> } };
      (axiosErr as Record<string, unknown>).code = 'ERR_BAD_REQUEST';
      (axiosErr as Record<string, unknown>).config = { method: 'GET', url: '/private', _retry: false };
      (axiosErr as Record<string, unknown>).response = { status: 401, data: { detail: 'Unauthorized' }, headers: {} };

      try {
        await errorHandler!(axiosErr);
        expect.fail('Should have thrown');
      } catch (e) {
        expect(e).toBeDefined();
        expect(authSpy).toHaveBeenCalled();
      }

      window.removeEventListener('auth:unauthorized', authSpy);
    });

    it('rejects if already retrying', async () => {
      localStorage.setItem(REFRESH_KEY, 'my-refresh');

      let errorHandler: ((error: unknown) => Promise<unknown>) | null = null;
      mockAxiosInstance.interceptors.response.use.mockImplementation(
        (_s: (response: unknown) => unknown, e: (error: unknown) => Promise<unknown>) => {
          errorHandler = e;
        },
      );

      await import('../instance');

      const config = {
        method: 'GET' as string,
        url: '/private',
        _retry: true,
        headers: {} as Record<string, string>,
      };

      const axiosErr = new (await import('axios')).AxiosError(
        'Unauthorized',
      ) as Error & { code?: string; config?: typeof config; response?: { status: number; data: unknown; headers: Record<string, string> } };
      (axiosErr as Record<string, unknown>).code = 'ERR_BAD_REQUEST';
      (axiosErr as Record<string, unknown>).config = config;
      (axiosErr as Record<string, unknown>).response = { status: 401, data: { detail: 'Unauthorized' }, headers: {} };

      try {
        await errorHandler!(axiosErr);
        expect.fail('Should have thrown');
      } catch (e) {
        expect(e).toBeDefined();
      }
    });

    it('refreshes token on 401 and retries', async () => {
      localStorage.setItem(REFRESH_KEY, 'my-refresh-token');

      const mockRefresh = await import('../auth');
      (mockRefresh.refreshTokens as ReturnType<typeof vi.fn>).mockResolvedValue({
        access_token: 'new-access',
        refresh_token: 'new-refresh',
      });

      let errorHandler: ((error: unknown) => Promise<unknown>) | null = null;
      mockAxiosInstance.interceptors.response.use.mockImplementation(
        (_s: (response: unknown) => unknown, e: (error: unknown) => Promise<unknown>) => {
          errorHandler = e;
        },
      );

      await import('../instance');

      const axiosErr = new (await import('axios')).AxiosError(
        'Unauthorized',
      ) as Error & { code?: string; config?: { method: string; url: string; _retry?: boolean; headers: Record<string, string> }; response?: { status: number; data: unknown; headers: Record<string, string> } };
      (axiosErr as Record<string, unknown>).code = 'ERR_BAD_REQUEST';
      (axiosErr as Record<string, unknown>).config = {
        method: 'GET',
        url: '/private',
        _retry: false,
        headers: {} as Record<string, string>,
      };
      (axiosErr as Record<string, unknown>).response = { status: 401, data: { detail: 'Unauthorized' }, headers: {} };

      try {
        await errorHandler!(axiosErr);
      } catch {
      }

      expect(mockRefresh.refreshTokens).toHaveBeenCalledWith('my-refresh-token');
    });

    it('dispatches auth:unauthorized when refresh fails', async () => {
      localStorage.setItem(REFRESH_KEY, 'bad-refresh');

      const mockRefresh = await import('../auth');
      (mockRefresh.refreshTokens as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Refresh failed'));

      let errorHandler: ((error: unknown) => Promise<unknown>) | null = null;
      mockAxiosInstance.interceptors.response.use.mockImplementation(
        (_s: (response: unknown) => unknown, e: (error: unknown) => Promise<unknown>) => {
          errorHandler = e;
        },
      );

      const authSpy = vi.fn();
      window.addEventListener('auth:unauthorized', authSpy);

      await import('../instance');

      const axiosErr = new (await import('axios')).AxiosError(
        'Unauthorized',
      ) as Error & { code?: string; config?: { method: string; url: string; _retry?: boolean; headers: Record<string, string> }; response?: { status: number; data: unknown; headers: Record<string, string> } };
      (axiosErr as Record<string, unknown>).code = 'ERR_BAD_REQUEST';
      (axiosErr as Record<string, unknown>).config = {
        method: 'GET',
        url: '/private',
        _retry: false,
        headers: {} as Record<string, string>,
      };
      (axiosErr as Record<string, unknown>).response = { status: 401, data: { detail: 'Unauthorized' }, headers: {} };

      try {
        await errorHandler!(axiosErr);
        expect.fail('Should have thrown');
      } catch (e) {
        expect(e).toBeDefined();
        expect(authSpy).toHaveBeenCalled();
      }

      window.removeEventListener('auth:unauthorized', authSpy);
    });
  });
});
