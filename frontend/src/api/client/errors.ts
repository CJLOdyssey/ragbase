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

function toApiError(
  status: number,
  message: string,
  data: Record<string, unknown> | undefined,
  retryAfter: unknown,
): never {
  switch (status) {
    case 401: {
      window.dispatchEvent(
        new CustomEvent('auth:unauthorized', { detail: { status: 401 } }),
      );
      throw new ApiError(message, status, 'UNAUTHORIZED', data);
    }
    case 403:
      // 403（权限/会话失效）与 401 同处理：触发登出，避免 UI 停留在
      // 已失效会话状态。
      window.dispatchEvent(
        new CustomEvent('auth:unauthorized', { detail: { status: 403 } }),
      );
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
    return toApiError(status, message, data, retryAfter);
  }
  throw err;
}
