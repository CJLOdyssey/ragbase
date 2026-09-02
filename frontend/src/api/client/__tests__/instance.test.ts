import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

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
    response?: {
      status: number;
      data: unknown;
      headers: Record<string, string>;
    };
    constructor(message: string) {
      super(message);
      this.name = 'AxiosError';
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

type RequestConfig = {
  headers: Record<string, string>;
  method?: string;
  url?: string;
};
type RequestInterceptor = (config: RequestConfig) => RequestConfig;
type ResponseSuccess = (response: unknown) => unknown;
type ResponseError = (error: unknown) => Promise<unknown>;
type MockResponse = {
  status: number;
  data: unknown;
  headers: Record<string, string>;
};

interface CapturedHandlers {
  request: RequestInterceptor | null;
  onFulfilled: ResponseSuccess | null;
  onRejected: ResponseError | null;
}

/**
 * Registers `use` mocks on the mocked axios instance and returns a mutable
 * object the interceptors instance.ts installs get captured into.
 */
function captureHandlers(): CapturedHandlers {
  const handlers: CapturedHandlers = {
    request: null,
    onFulfilled: null,
    onRejected: null,
  };
  mockAxiosInstance.interceptors.request.use.mockImplementation(
    (fn: RequestInterceptor) => {
      handlers.request = fn;
    },
  );
  mockAxiosInstance.interceptors.response.use.mockImplementation(
    (onFulfilled: ResponseSuccess, onRejected: ResponseError) => {
      handlers.onFulfilled = onFulfilled;
      handlers.onRejected = onRejected;
    },
  );
  return handlers;
}

/** Builds an AxiosError from the mocked axios module. */
async function makeAxiosError(
  message: string,
  config: Record<string, unknown> = {},
  response: MockResponse = { status: 500, data: {}, headers: {} },
  code = 'ERR_BAD_REQUEST',
) {
  const { AxiosError } = await import('axios');
  const err = new AxiosError(message);
  err.code = code;
  err.config = config;
  err.response = response;
  return err;
}

/** Builds a 401 AxiosError for the given request URL. */
const make401 = (url: string) =>
  makeAxiosError(
    'Unauthorized',
    { method: 'GET', url, _retry: false, headers: {} },
    { status: 401, data: { detail: 'Unauthorized' }, headers: {} },
  );

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

  describe('request interceptor', () => {
    it('does not add Authorization header (access token is httpOnly cookie)', async () => {
      const handlers = captureHandlers();
      await import('../instance');
      const result = handlers.request!({ headers: {} });
      expect(result.headers.Authorization).toBeUndefined();
    });

    it('does not add X-User-ID header (user identity comes from JWT cookie)', async () => {
      localStorage.setItem('ragbase_user_id', 'legacy-uid');
      const handlers = captureHandlers();
      await import('../instance');
      const result = handlers.request!({
        headers: {},
        method: 'GET',
        url: '/test',
      });
      expect(result.headers['X-User-ID']).toBeUndefined();
      expect(result.headers.Authorization).toBeUndefined();
    });
  });

  describe('response interceptor', () => {
    it('returns successful response as-is', async () => {
      const handlers = captureHandlers();
      await import('../instance');
      const response = {
        config: { method: 'GET', url: '/test' },
        status: 200,
        data: { ok: true },
      };
      expect(handlers.onFulfilled!(response)).toBe(response);
    });

    it('rejects non-401 errors', async () => {
      const handlers = captureHandlers();
      await import('../instance');
      const axiosErr = await makeAxiosError(
        'Not Found',
        { method: 'GET', url: '/missing', _retry: false },
        { status: 404, data: { detail: 'Not Found' }, headers: {} },
      );
      await expect(handlers.onRejected!(axiosErr)).rejects.toBeDefined();
    });

    it('rejects if already retrying', async () => {
      const handlers = captureHandlers();
      const config = {
        method: 'GET' as string,
        url: '/private',
        _retry: true,
        headers: {} as Record<string, string>,
      };
      await import('../instance');
      const axiosErr = await makeAxiosError('Unauthorized', config, {
        status: 401,
        data: { detail: 'Unauthorized' },
        headers: {},
      });
      await expect(handlers.onRejected!(axiosErr)).rejects.toBeDefined();
    });

    it('refreshes token on 401 and retries', async () => {
      const mockRefresh = await import('../auth');
      (mockRefresh.refreshTokens as ReturnType<typeof vi.fn>).mockResolvedValue(
        undefined,
      );
      const handlers = captureHandlers();
      await import('../instance');
      const axiosErr = await make401('/private');
      try {
        await handlers.onRejected!(axiosErr);
      } catch {}
      expect(mockRefresh.refreshTokens).toHaveBeenCalledWith();
    });

    it('does not dispatch auth:unauthorized on refresh failure (errors.ts owns it)', async () => {
      const mockRefresh = await import('../auth');
      (mockRefresh.refreshTokens as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('Refresh failed'),
      );
      const handlers = captureHandlers();
      const authSpy = vi.fn();
      window.addEventListener('auth:unauthorized', authSpy);
      await import('../instance');
      const axiosErr = await make401('/private');
      await expect(handlers.onRejected!(axiosErr)).rejects.toBeDefined();
      // 401/403 的登出派发由 errors.ts normalizeError 单点负责；
      // instance 只做刷新编排，不重复派发（避免双发 auth:unauthorized）。
      expect(authSpy).not.toHaveBeenCalled();
      window.removeEventListener('auth:unauthorized', authSpy);
    });

    it('settles queued 401 requests when the in-flight refresh fails (no hang)', async () => {
      let rejectRefresh!: (err: Error) => void;
      const refreshGate = new Promise<void>((_, rej) => {
        rejectRefresh = rej;
      });
      const mockRefresh = await import('../auth');
      (mockRefresh.refreshTokens as ReturnType<typeof vi.fn>).mockReturnValue(
        refreshGate,
      );
      const handlers = captureHandlers();
      await import('../instance');

      // Two parallel 401s (StrictMode double-init): the first starts the
      // refresh, the second queues behind it.
      const err1 = await make401('/private');
      const err2 = await make401('/private-2');
      const p1 = handlers.onRejected!(err1);
      const p2 = handlers.onRejected!(err2);

      rejectRefresh(new Error('Refresh failed'));

      // Both callers must settle — the queued one used to be dropped and
      // stayed pending forever, leaving AuthContext's Promise.all unresolved
      // and loading stuck on the skeleton. With the single-flight coordinator
      // both reject with their own 401 error; the refresh failure surfaces via
      // the auth:unauthorized event.
      await expect(p1).rejects.toBeDefined();
      await expect(p2).rejects.toBeDefined();
      // Queued retry is single-shot: a 401 on retry rejects instead of
      // recursing into another refresh.
      expect(err2.config?._retry).toBe(true);
    });
  });
});
