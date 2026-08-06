import api from './instance';

export interface AuthConfigResponse {
  enabled: boolean;
  mode: string;
}

export interface UserResponse {
  id: string;
  email: string;
  username: string | null;
  roles: string[];
  is_verified: boolean;
}

export interface AuthTokensResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
}

export interface MessageResponse {
  message: string;
}

export interface EmailHintResponse {
  message: string;
  email_hint: string;
}

export async function login(email: string, password: string, rememberMe?: boolean): Promise<AuthTokensResponse> {
  const { data } = await api.post<AuthTokensResponse>('/auth/login', { email, password, remember_me: rememberMe });
  return data;
}

export async function sendRegisterCode(email: string): Promise<EmailHintResponse> {
  const { data } = await api.post<EmailHintResponse>('/auth/send-register-code', { email });
  return data;
}

export async function register(email: string, code: string, password: string): Promise<AuthTokensResponse> {
  const { data } = await api.post<AuthTokensResponse>('/auth/register', { email, code, password });
  return data;
}

export async function verify(email: string, code: string): Promise<AuthTokensResponse> {
  const { data } = await api.post<AuthTokensResponse>('/auth/verify', { email, code });
  return data;
}

export async function refreshTokens(refreshToken: string): Promise<AuthTokensResponse> {
  const { data } = await api.post<AuthTokensResponse>('/auth/refresh', { refresh_token: refreshToken });
  return data;
}

export async function forgotPassword(email: string): Promise<MessageResponse> {
  const { data } = await api.post<MessageResponse>('/auth/forgot-password', { email });
  return data;
}

export async function resetPassword(email: string, code: string, newPassword: string): Promise<MessageResponse> {
  const { data } = await api.post<MessageResponse>('/auth/reset-password', { email, code, new_password: newPassword });
  return data;
}

export async function logout(refreshToken: string): Promise<void> {
  await api.post('/auth/logout', { refresh_token: refreshToken });
}

export async function getMe(): Promise<UserResponse> {
  const { data } = await api.get<UserResponse>('/auth/me');
  return data;
}

export async function getAuthConfig(): Promise<AuthConfigResponse> {
  const { data } = await api.get<AuthConfigResponse>('/auth/config');
  return data;
}

export async function resendVerification(email: string): Promise<MessageResponse> {
  const { data } = await api.post<MessageResponse>('/auth/resend-verification', { email });
  return data;
}

export async function mergeGuestData(guestId: string): Promise<void> {
  await api.post('/auth/merge', { guest_id: guestId });
}
