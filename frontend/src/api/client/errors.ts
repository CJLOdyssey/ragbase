import { AxiosError } from 'axios';
import Logger from '../../utils/logger';

// ---- Custom Error Class ----

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'TimeoutError';
  }
}

// 认证表单类端点：401/403 是凭证校验的业务结果（密码错误、验证码错误等），
// 不是会话失效，不得触发全局登出副作用。
const AUTH_CREDENTIAL_PATHS = [
  '/auth/login',
  '/auth/register',
  '/auth/verify',
  '/auth/send-register-code',
  '/auth/resend-verification',
  '/auth/forgot-password',
  '/auth/reset-password',
  '/auth/change-password',
];

function isCredentialPath(url: string | undefined): boolean {
  if (!url) return false;
  return AUTH_CREDENTIAL_PATHS.some(
    (p) => url === p || url.startsWith(`${p}?`),
  );
}

function extractErrorMessage(
  data: Record<string, unknown> | undefined,
  fallback: string,
): string {
  const detail = data?.detail;
  if (typeof detail === 'string') return detail;
  const nested = (detail as { error?: { message?: string } } | undefined)?.error
    ?.message;
  if (nested) return nested;
  if (data?.message) return data.message as string;
  return fallback;
}

function dispatchUnauthorized(status: number, url: string | undefined): void {
  // 凭证校验类端点的 401/403 是正常业务错误（如密码错误），登出副作用
  // 由表单错误处理承担；只有会话失效类 401/403 才派发全局登出事件。
  if (isCredentialPath(url)) return;
  window.dispatchEvent(
    new CustomEvent('auth:unauthorized', { detail: { status } }),
  );
}

function toApiError(
  status: number,
  message: string,
  data: Record<string, unknown> | undefined,
  retryAfter: unknown,
  url?: string,
): never {
  switch (status) {
    case 401: {
      dispatchUnauthorized(401, url);
      throw new ApiError(message, status, 'UNAUTHORIZED', data);
    }
    case 403:
      // 403（权限/会话失效）与 401 同处理：触发登出，避免 UI 停留在
      // 已失效会话状态。
      dispatchUnauthorized(403, url);
      throw new ApiError(message, status, 'FORBIDDEN', data);
    case 404:
      throw new ApiError(message, status, 'NOT_FOUND', data);
    case 422:
      throw new ApiError(message, status, 'VALIDATION_ERROR', data);
    case 429:
      throw new ApiError(message, status, 'RATE_LIMITED', {
        ...data,
        retryAfter,
      });
    case 500:
    case 502:
    case 503:
    case 504:
      Logger.error(`Server error ${status}`, { message, status, data });
      throw new ApiError(message, status, 'SERVER_ERROR', data);
    default:
      Logger.warn(`Unhandled API error ${status}`, { message, status });
      throw new ApiError(message, status, 'UNKNOWN', data);
  }
}

export function normalizeError(err: unknown): never {
  if (err instanceof AxiosError) {
    if (err.code === 'ECONNABORTED') {
      throw new TimeoutError('Request timed out');
    }
    if (!err.response) {
      throw new NetworkError(err.message || 'Network error');
    }
    const status = err.response.status;
    const data = err.response.data as Record<string, unknown> | undefined;
    const message = extractErrorMessage(data, err.message);
    const retryAfter =
      status === 429 ? err.response.headers['retry-after'] : undefined;
    return toApiError(status, message, data, retryAfter, err.config?.url);
  }
  throw err;
}
