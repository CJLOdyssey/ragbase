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
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  withCredentials: true,
});

interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

if (api.interceptors?.request) {
  api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    // RBAC mode: user identity comes from httpOnly JWT cookie (auto-sent via withCredentials)
    // No X-User-ID header needed — backend reads user_id from JWT
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
    async (error: AxiosError) => {
      const originalRequest = error.config as RetryConfig;

      // 401 on non-auth routes → try refresh (single-flight)
      if (
        error.response?.status === 401 &&
        !originalRequest._retry &&
        !originalRequest.url?.startsWith('/auth/')
      ) {
        originalRequest._retry = true;
        try {
          await refreshAccessToken();
          return api.request(originalRequest);
        } catch (refreshError) {
          // 401/403 登出事件由 errors.ts normalizeError 单点派发
          // （/auth/refresh 的 401 已在内部拦截器归一化时派发过），
          // 此处不得重复派发；网络类失败本就不该触发登出。
          return Promise.reject(normalizeError(refreshError));
        }
      }

      return Promise.reject(normalizeError(error));
    },
  );
}

export default api;
