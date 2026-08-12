import axios, {
  type AxiosError,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios';
import { refreshTokens } from './auth';
import { normalizeError } from './errors';
import Logger from '../../utils/logger';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  withCredentials: true,
});

// Tokens live in httpOnly cookies only — JS never holds or reads them (OWASP).
// Access token is not readable from JS; refresh token is sent by the browser
// on /auth/refresh and /auth/logout via withCredentials.

/** Access token is an httpOnly cookie — not readable from JS. Returns null. */
export function getAccessToken(): string | null {
  return null;
}

interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

interface PendingRequest {
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
}

let isRefreshing = false;
let pendingQueue: Array<PendingRequest> = [];

if (api.interceptors?.request) {
  api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    // Access token is in httpOnly cookie (auto-sent via withCredentials), no Authorization header needed
    let uid = localStorage.getItem('ragbase_user_id');
    if (!uid) {
      uid =
        'u_' +
        Date.now().toString(36) +
        '_' +
        Math.random().toString(36).slice(2, 8);
      localStorage.setItem('ragbase_user_id', uid);
    }
    config.headers['X-User-ID'] = uid;
    Logger.debug('[API] %s %s', config.method?.toUpperCase(), config.url);
    return config;
  });
}

if (api.interceptors?.response) {
  api.interceptors.response.use(
    (response: AxiosResponse) => {
      Logger.debug(
        '[API] %s %s -> %s',
        response.config.method?.toUpperCase(),
        response.config.url,
        response.status,
      );
      return response;
    },
    async (error: unknown) => {
      const axiosError = error as AxiosError;
      const retryConfig = axiosError.config as RetryConfig | undefined;
      const status = axiosError.response?.status ?? 0;
      const method = retryConfig?.method?.toUpperCase() ?? '?';
      const url = retryConfig?.url ?? '?';
      if (status !== 401) {
        Logger.error(
          '[API] %s %s -> %s %s',
          method,
          url,
          status,
          axiosError.message,
        );
      }
      if (!retryConfig || retryConfig._retry || status !== 401) {
        return Promise.reject(normalizeError(error));
      }

      // Refresh endpoint failures are terminal — never recurse into this
      // interceptor or queue behind a refresh that is itself failing, or
      // isRefreshing would stay true forever and stall every request
      // (用户菜单等依赖 loading 收敛的 UI 会永久骨架).
      if (retryConfig.url === '/auth/refresh') {
        return Promise.reject(normalizeError(error));
      }

      if (isRefreshing) {
        // Queue behind the in-flight refresh. Entries must carry a reject —
        // if the refresh fails and queued promises are dropped unsolved, the
        // caller hangs forever. With StrictMode's double-mounted AuthContext
        // init, two parallel getMe 401s race: one starts the refresh, the
        // other queues, and a failed refresh leaves Promise.all pending →
        // loading never converges → avatar skeleton stuck.
        retryConfig._retry = true;
        return new Promise<unknown>((resolve, reject) => {
          pendingQueue.push({ resolve, reject });
        }).then(() => api(retryConfig));
      }

      retryConfig._retry = true;
      isRefreshing = true;

      try {
        await refreshTokens();
        pendingQueue.forEach(({ resolve }) => resolve(undefined));
        pendingQueue = [];
        // New access_token was set as httpOnly cookie by server — auto-sent on retry
        return api(retryConfig);
      } catch (err) {
        // Drain the queue by rejecting every entry — dropping it would leave
        // the queued 401 callers pending forever (same hang as above).
        const failed = pendingQueue;
        pendingQueue = [];
        failed.forEach(({ reject }) => reject(err));
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
        return Promise.reject(normalizeError(error));
      } finally {
        isRefreshing = false;
      }
    },
  );
}

export default api;
