import { describe, it, expect } from 'vitest';
import { AxiosError, AxiosHeaders } from 'axios';

import { ApiError, NetworkError, TimeoutError, normalizeError } from '../errors';

describe('ApiError', { tags: ['unit'] }, () => {
  it('constructs with name Apierror', () => {
    const err = new ApiError('msg', 400, 'BAD_REQUEST', { detail: 'x' });
    expect(err.name).toBe('ApiError');
    expect(err.message).toBe('msg');
    expect(err.status).toBe(400);
    expect(err.code).toBe('BAD_REQUEST');
    expect(err.details).toEqual({ detail: 'x' });
  });
});

describe('NetworkError', { tags: ['unit'] }, () => {
  it('constructs with name NetworkError', () => {
    const err = new NetworkError('offline');
    expect(err.name).toBe('NetworkError');
    expect(err.message).toBe('offline');
  });
});

describe('TimeoutError', { tags: ['unit'] }, () => {
  it('constructs with name TimeoutError', () => {
    const err = new TimeoutError('timed out');
    expect(err.name).toBe('TimeoutError');
    expect(err.message).toBe('timed out');
  });
});

describe('normalizeError', { tags: ['unit'] }, () => {
  it('throws TimeoutError for ECONNABORTED', () => {
    const axiosErr = new AxiosError('timeout', 'ECONNABORTED');
    expect(() => normalizeError(axiosErr)).toThrow(TimeoutError);
  });

  it('throws NetworkError when no response', () => {
    const axiosErr = new AxiosError('Network Error', 'ERR_NETWORK');
    expect(() => normalizeError(axiosErr)).toThrow(NetworkError);
  });

  it('throws ApiError with UNAUTHORIZED for 401', () => {
    const axiosErr = new AxiosError(
      'Unauthorized',
      'ERR_BAD_RESPONSE',
      undefined,
      undefined,
      { status: 401, data: { detail: 'Invalid token' }, headers: {}, statusText: 'Unauthorized', config: { headers: new AxiosHeaders() } },
    );
    expect(() => normalizeError(axiosErr)).toThrow(ApiError);
    try { normalizeError(axiosErr); } catch (e) {
      const apiErr = e as ApiError;
      expect(apiErr.code).toBe('UNAUTHORIZED');
      expect(apiErr.status).toBe(401);
    }
  });

  it('throws ApiError with FORBIDDEN for 403', () => {
    const axiosErr = new AxiosError(
      'Forbidden',
      'ERR_BAD_RESPONSE',
      undefined,
      undefined,
      { status: 403, data: { detail: 'No access' }, headers: {}, statusText: 'Forbidden', config: { headers: new AxiosHeaders() } },
    );
    expect(() => normalizeError(axiosErr)).toThrow(ApiError);
    try { normalizeError(axiosErr); } catch (e) {
      const apiErr = e as ApiError;
      expect(apiErr.code).toBe('FORBIDDEN');
    }
  });

  it('throws ApiError with NOT_FOUND for 404', () => {
    const axiosErr = new AxiosError(
      'Not Found',
      'ERR_BAD_RESPONSE',
      undefined,
      undefined,
      { status: 404, data: { message: 'Not found' }, headers: {}, statusText: 'Not Found', config: { headers: new AxiosHeaders() } },
    );
    expect(() => normalizeError(axiosErr)).toThrow(ApiError);
    try { normalizeError(axiosErr); } catch (e) {
      const apiErr = e as ApiError;
      expect(apiErr.code).toBe('NOT_FOUND');
    }
  });

  it('throws ApiError with VALIDATION_ERROR for 422', () => {
    const axiosErr = new AxiosError(
      'Unprocessable',
      'ERR_BAD_RESPONSE',
      undefined,
      undefined,
      { status: 422, data: { detail: 'Invalid input' }, headers: {}, statusText: 'Unprocessable', config: { headers: new AxiosHeaders() } },
    );
    expect(() => normalizeError(axiosErr)).toThrow(ApiError);
    try { normalizeError(axiosErr); } catch (e) {
      const apiErr = e as ApiError;
      expect(apiErr.code).toBe('VALIDATION_ERROR');
    }
  });

  it('throws ApiError with RATE_LIMITED for 429', () => {
    const headers = new AxiosHeaders();
    headers.set('retry-after', '60');
    const axiosErr = new AxiosError(
      'Too Many Requests',
      'ERR_BAD_RESPONSE',
      undefined,
      undefined,
      { status: 429, data: { detail: 'Rate limited' }, headers, statusText: 'Too Many', config: { headers: new AxiosHeaders() } },
    );
    expect(() => normalizeError(axiosErr)).toThrow(ApiError);
    try { normalizeError(axiosErr); } catch (e) {
      const apiErr = e as ApiError;
      expect(apiErr.code).toBe('RATE_LIMITED');
    }
  });

  it('throws ApiError with SERVER_ERROR for 500', () => {
    const axiosErr = new AxiosError(
      'Internal Error',
      'ERR_BAD_RESPONSE',
      undefined,
      undefined,
      { status: 500, data: { detail: 'Boom' }, headers: {}, statusText: 'Error', config: { headers: new AxiosHeaders() } },
    );
    expect(() => normalizeError(axiosErr)).toThrow(ApiError);
    try { normalizeError(axiosErr); } catch (e) {
      const apiErr = e as ApiError;
      expect(apiErr.code).toBe('SERVER_ERROR');
    }
  });

  it('throws ApiError with SERVER_ERROR for 502', () => {
    const axiosErr = new AxiosError('', 'ERR_BAD_RESPONSE', undefined, undefined, {
      status: 502, data: { detail: 'Bad Gateway' }, headers: {}, statusText: 'Bad Gateway', config: { headers: new AxiosHeaders() },
    });
    expect(() => normalizeError(axiosErr)).toThrow(ApiError);
    try { normalizeError(axiosErr); } catch (e) {
      expect((e as ApiError).code).toBe('SERVER_ERROR');
    }
  });

  it('throws ApiError with SERVER_ERROR for 503', () => {
    const axiosErr = new AxiosError('', 'ERR_BAD_RESPONSE', undefined, undefined, {
      status: 503, data: {}, headers: {}, statusText: 'Unavailable', config: { headers: new AxiosHeaders() },
    });
    expect(() => normalizeError(axiosErr)).toThrow(ApiError);
    try { normalizeError(axiosErr); } catch (e) {
      expect((e as ApiError).code).toBe('SERVER_ERROR');
    }
  });

  it('throws ApiError with SERVER_ERROR for 504', () => {
    const axiosErr = new AxiosError('', 'ERR_BAD_RESPONSE', undefined, undefined, {
      status: 504, data: {}, headers: {}, statusText: 'Gateway Timeout', config: { headers: new AxiosHeaders() },
    });
    expect(() => normalizeError(axiosErr)).toThrow(ApiError);
    try { normalizeError(axiosErr); } catch (e) {
      expect((e as ApiError).code).toBe('SERVER_ERROR');
    }
  });

  it('throws ApiError with UNKNOWN for unhandled status', () => {
    const axiosErr = new AxiosError('', 'ERR_BAD_RESPONSE', undefined, undefined, {
      status: 418, data: {}, headers: {}, statusText: "I'm a teapot", config: { headers: new AxiosHeaders() },
    });
    expect(() => normalizeError(axiosErr)).toThrow(ApiError);
    try { normalizeError(axiosErr); } catch (e) {
      expect((e as ApiError).code).toBe('UNKNOWN');
    }
  });

  it('re-throws non-AxiosError errors', () => {
    const err = new Error('plain error');
    expect(() => normalizeError(err)).toThrow('plain error');
  });

  it('uses default message when no error message on network error', () => {
    const axiosErr = new AxiosError('', 'ERR_NETWORK');
    expect(() => normalizeError(axiosErr)).toThrow('Network error');
  });

  it('prefers detail over message in response data', () => {
    const axiosErr = new AxiosError('', 'ERR_BAD_RESPONSE', undefined, undefined, {
      status: 400, data: { detail: 'custom detail', message: 'custom message' },
      headers: {}, statusText: 'Bad', config: { headers: new AxiosHeaders() },
    });
    try { normalizeError(axiosErr); } catch (e) {
      expect((e as ApiError).message).toBe('custom detail');
    }
  });

  it('falls back to axios error message when no response data', () => {
    const axiosErr = new AxiosError('fallback msg', 'ERR_BAD_RESPONSE', undefined, undefined, {
      status: 400, data: undefined, headers: {}, statusText: 'Bad', config: { headers: new AxiosHeaders() },
    });
    try { normalizeError(axiosErr); } catch (e) {
      expect((e as ApiError).message).toBe('fallback msg');
    }
  });
});
