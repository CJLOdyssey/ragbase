import { refreshTokens } from './auth';

/**
 * Single-flight refresh coordinator.
 *
 * Both the axios 401 interceptor and AuthContext trigger a refresh. The backend
 * rotates the refresh token, so two concurrent refreshes race: one wins, the
 * other 401s and is wrongly treated as "session expired" (logout + cleared
 * model selection). This collapses concurrent refreshes into ONE request.
 * The refresh token lives in an httpOnly cookie — sent automatically.
 */
let refreshPromise: Promise<void> | null = null;

export function refreshAccessToken(): Promise<void> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = refreshTokens().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}
