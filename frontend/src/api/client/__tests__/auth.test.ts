import { describe, it, expect, vi, beforeEach } from 'vitest';

const { mockApi } = vi.hoisted(() => ({
  mockApi: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('../instance', () => ({ default: mockApi }));

import {
  login,
  sendRegisterCode,
  register,
  verify,
  refreshTokens,
  forgotPassword,
  resetPassword,
  logout,
  getMe,
  getAuthConfig,
  resendVerification,
  mergeGuestData,
} from '../auth';

beforeEach(() => {
  vi.resetAllMocks();
});

describe('login', { tags: ['unit'] }, () => {
  it('calls POST /auth/login with email and password', async () => {
    const mockResponse = { data: { access_token: 'at', refresh_token: 'rt', token_type: 'bearer', expires_in: 3600, user: { id: 'u1', email: 'a@b.com', username: null, roles: [], is_verified: true } } };
    mockApi.post.mockResolvedValue(mockResponse);

    const result = await login('a@b.com', 'pass');

    expect(mockApi.post).toHaveBeenCalledWith('/auth/login', { email: 'a@b.com', password: 'pass', remember_me: undefined });
    expect(result).toEqual(mockResponse.data);
  });

  it('passes rememberMe when true', async () => {
    const mockResponse = { data: { access_token: 'at', refresh_token: 'rt', token_type: 'bearer', expires_in: 3600, user: { id: 'u1', email: 'a@b.com', username: null, roles: [], is_verified: true } } };
    mockApi.post.mockResolvedValue(mockResponse);

    await login('a@b.com', 'pass', true);

    expect(mockApi.post).toHaveBeenCalledWith('/auth/login', { email: 'a@b.com', password: 'pass', remember_me: true });
  });
});

describe('sendRegisterCode', { tags: ['unit'] }, () => {
  it('calls POST /auth/send-register-code', async () => {
    const mockResponse = { data: { message: 'Code sent', email_hint: 'a***@b.com' } };
    mockApi.post.mockResolvedValue(mockResponse);

    const result = await sendRegisterCode('a@b.com');

    expect(mockApi.post).toHaveBeenCalledWith('/auth/send-register-code', { email: 'a@b.com' });
    expect(result).toEqual(mockResponse.data);
  });
});

describe('register', { tags: ['unit'] }, () => {
  it('calls POST /auth/register', async () => {
    const mockResponse = { data: { access_token: 'at', refresh_token: 'rt', token_type: 'bearer', expires_in: 3600, user: { id: 'u1', email: 'a@b.com', username: null, roles: [], is_verified: true } } };
    mockApi.post.mockResolvedValue(mockResponse);

    const result = await register('a@b.com', 'code123', 'pass');

    expect(mockApi.post).toHaveBeenCalledWith('/auth/register', { email: 'a@b.com', code: 'code123', password: 'pass' });
    expect(result).toEqual(mockResponse.data);
  });
});

describe('verify', { tags: ['unit'] }, () => {
  it('calls POST /auth/verify', async () => {
    const mockResponse = { data: { access_token: 'at', refresh_token: 'rt', token_type: 'bearer', expires_in: 3600, user: { id: 'u1', email: 'a@b.com', username: null, roles: [], is_verified: true } } };
    mockApi.post.mockResolvedValue(mockResponse);

    const result = await verify('a@b.com', 'code123');

    expect(mockApi.post).toHaveBeenCalledWith('/auth/verify', { email: 'a@b.com', code: 'code123' });
    expect(result).toEqual(mockResponse.data);
  });
});

describe('refreshTokens', { tags: ['unit'] }, () => {
  it('calls POST /auth/refresh with refresh token', async () => {
    const mockResponse = { data: { access_token: 'new-at', refresh_token: 'new-rt', token_type: 'bearer', expires_in: 3600, user: { id: 'u1', email: 'a@b.com', username: null, roles: [], is_verified: true } } };
    mockApi.post.mockResolvedValue(mockResponse);

    const result = await refreshTokens('old-rt');

    expect(mockApi.post).toHaveBeenCalledWith('/auth/refresh', { refresh_token: 'old-rt' });
    expect(result).toEqual(mockResponse.data);
  });
});

describe('forgotPassword', { tags: ['unit'] }, () => {
  it('calls POST /auth/forgot-password', async () => {
    const mockResponse = { data: { message: 'Email sent' } };
    mockApi.post.mockResolvedValue(mockResponse);

    const result = await forgotPassword('a@b.com');

    expect(mockApi.post).toHaveBeenCalledWith('/auth/forgot-password', { email: 'a@b.com' });
    expect(result).toEqual(mockResponse.data);
  });
});

describe('resetPassword', { tags: ['unit'] }, () => {
  it('calls POST /auth/reset-password', async () => {
    const mockResponse = { data: { message: 'Password reset' } };
    mockApi.post.mockResolvedValue(mockResponse);

    const result = await resetPassword('a@b.com', 'code123', 'newpass');

    expect(mockApi.post).toHaveBeenCalledWith('/auth/reset-password', { email: 'a@b.com', code: 'code123', new_password: 'newpass' });
    expect(result).toEqual(mockResponse.data);
  });
});

describe('logout', { tags: ['unit'] }, () => {
  it('calls POST /auth/logout', async () => {
    mockApi.post.mockResolvedValue({});

    await logout('rt');

    expect(mockApi.post).toHaveBeenCalledWith('/auth/logout', { refresh_token: 'rt' });
  });
});

describe('getMe', { tags: ['unit'] }, () => {
  it('calls GET /auth/me', async () => {
    const mockResponse = { data: { id: 'u1', email: 'a@b.com', username: 'test', roles: ['user'], is_verified: true } };
    mockApi.get.mockResolvedValue(mockResponse);

    const result = await getMe();

    expect(mockApi.get).toHaveBeenCalledWith('/auth/me');
    expect(result).toEqual(mockResponse.data);
  });
});

describe('getAuthConfig', { tags: ['unit'] }, () => {
  it('calls GET /auth/config', async () => {
    const mockResponse = { data: { enabled: true, mode: 'rbac' } };
    mockApi.get.mockResolvedValue(mockResponse);

    const result = await getAuthConfig();

    expect(mockApi.get).toHaveBeenCalledWith('/auth/config');
    expect(result).toEqual(mockResponse.data);
  });
});

describe('resendVerification', { tags: ['unit'] }, () => {
  it('calls POST /auth/resend-verification', async () => {
    const mockResponse = { data: { message: 'Verification resent' } };
    mockApi.post.mockResolvedValue(mockResponse);

    const result = await resendVerification('a@b.com');

    expect(mockApi.post).toHaveBeenCalledWith('/auth/resend-verification', { email: 'a@b.com' });
    expect(result).toEqual(mockResponse.data);
  });
});

describe('mergeGuestData', { tags: ['unit'] }, () => {
  it('calls POST /auth/merge', async () => {
    mockApi.post.mockResolvedValue({});

    await mergeGuestData('guest-123');

    expect(mockApi.post).toHaveBeenCalledWith('/auth/merge', { guest_id: 'guest-123' });
  });
});
