import axios, {
  type AxiosError,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios';
import { normalizeError } from './errors';
import { refreshAccessToken } from './refresh';
import Logger from '../../utils/logger';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  withCredentials: true,
});

/**
 * Tokens live in httpOnly cookies only — JS never holds or reads them (OWASP).
 * The access token is not readable from JS; the refresh token is sent by the
 * browser on /auth/refresh and /auth/logout via withCredentials.
 */
export function getAccessToken(): string | null {
  return null;
}

interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

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
      // interceptor or queue behind a refresh that is itself failing.
      if (retryConfig.url === '/auth/refresh') {
        return Promise.reject(normalizeError(error));
      }

      // Single-flight refresh: refreshAccessToken collapses concurrent 401s
      // (interceptor + AuthContext) into one backend call — the server rotates
      // the refresh token, so a race would 401 one path and log the user out.
      retryConfig._retry = true;
      try {
        await refreshAccessToken();
        // New access_token was set as httpOnly cookie by server — auto-sent on retry
        return api(retryConfig);
      } catch {
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
        return Promise.reject(normalizeError(error));
      }
    },
  );
}

export default api;
