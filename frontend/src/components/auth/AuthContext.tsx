import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import {
  forgotPassword as apiForgotPassword,
  login as apiLogin,
  logout as apiLogout,
  mergeGuestData as apiMergeGuestData,
  register as apiRegister,
  resendVerification as apiResendVerification,
  resetPassword as apiResetPassword,
  sendRegisterCode as apiSendRegisterCode,
  verify as apiVerify,
  getAuthConfig,
  getMe,
} from '../../api/client/auth';
import { refreshAccessToken } from '../../api/client/refresh';
import { useChatStore } from '../../stores/chatStore';

function clearLocalConversations() {
  try {
    localStorage.removeItem('ragbase-conversations');
    localStorage.removeItem('ragbase-sessions-cache');
    window.dispatchEvent(new Event('ragbase-conversations-updated'));
  } catch {}
}

async function mergeGuest() {
  try {
    const guestId = localStorage.getItem('ragbase_user_id');
    if (guestId) await apiMergeGuestData(guestId);
  } catch {
    /* merge is best-effort */
  }
}

export type AuthModalView =
  'login' | 'register' | 'verify' | 'forgot' | 'reset';

interface AuthUser {
  userId: string;
  email: string;
  username: string | null;
  roles: string[];
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  legacyMode: boolean;
  isAuthenticated: boolean;
  loginModalOpen: boolean;
  loginModalView: AuthModalView;
  loginModalEmail: string;
  login: (
    email: string,
    password: string,
    rememberMe?: boolean,
  ) => Promise<void>;
  register: (email: string, code: string, password: string) => Promise<void>;
  verify: (email: string, code: string) => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  resetPassword: (
    email: string,
    code: string,
    newPassword: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
  resendVerification: (email: string) => Promise<void>;
  sendRegisterCode: (email: string) => Promise<{ emailHint: string }>;
  openLoginModal: (view?: AuthModalView) => void;
  closeLoginModal: () => void;
  setLoginModalEmail: (email: string) => void;
  setLoginModalView: (view: AuthModalView) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// 页面常驻期间定时续期 access_token（httpOnly cookie 轮换），刷新页面时
// cookie 仍然新鲜 → getMe 直接 200，跳过 401→refresh→me 串行链（token 保鲜机制，刷新体验更丝滑）。
const REFRESH_INTERVAL_MS = 10 * 60 * 1000;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [legacyMode, setLegacyMode] = useState(true);
  const [loading, setLoading] = useState(true);
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [loginModalView, setLoginModalView] = useState<AuthModalView>('login');
  const [loginModalEmail, setLoginModalEmail] = useState('');
  const refreshTimerRef = useRef<number | null>(null);
  const lastRefreshRef = useRef(0);

  const refreshSession = useCallback(async (): Promise<boolean> => {
    // Single-flight refresh: the axios 401 interceptor and this timer share the
    // same coordinator so the rotated refresh_token is never double-consumed
    // (a race would 401 one path and spuriously log the user out).
    try {
      await refreshAccessToken();
      lastRefreshRef.current = Date.now();
      return true;
    } catch (err) {
      // refresh 失败（401/403）→ 会话过期：登出，避免"幽灵登录"后业务请求
      // 以 anonymous 身份报误导性 400。网络错误不登出（由定时器重试）。
      const status = (err as { response?: { status?: number } })?.response
        ?.status;
      if (status === 401 || status === 403) {
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      }
      return false;
    }
  }, []);

  useEffect(() => {
    // 登录后每 10 分钟续期；失败（后端重启/瞬时故障）时 60 秒快速重试，
    // 避免 access_token 在 TTL 内过期且无人续期。后台标签页计时器被节流，
    // 切回前台时若超期立即补一次。
    const start = () => {
      lastRefreshRef.current = Date.now();
      if (refreshTimerRef.current !== null) return;
      let failureBackoff = false;
      refreshTimerRef.current = window.setInterval(async () => {
        const ok = await refreshSession();
        if (!ok && !failureBackoff) {
          failureBackoff = true;
          window.setTimeout(() => {
            failureBackoff = false;
            void refreshSession();
          }, 60_000);
        }
      }, REFRESH_INTERVAL_MS);
    };
    const stop = () => {
      if (refreshTimerRef.current !== null) {
        window.clearInterval(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
    };
    const handleVisibility = () => {
      if (
        document.visibilityState === 'visible' &&
        Date.now() - lastRefreshRef.current >= REFRESH_INTERVAL_MS
      ) {
        void refreshSession();
      }
    };
    const handleUnauthorized = () => {
      setUser(null);
      clearLocalConversations();
      // 模型选择/最近模型是用户偏好，与认证无关 —— 不清除，否则重新登录后
      // 仍走默认模型（历史上"一直走 deepseek"的根因之一）。
      setLoginModalOpen(true);
    };
    window.addEventListener('auth:login', start);
    window.addEventListener('auth:logout', stop);
    window.addEventListener('auth:unauthorized', stop);
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      window.removeEventListener('auth:login', start);
      window.removeEventListener('auth:logout', stop);
      window.removeEventListener('auth:unauthorized', stop);
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
      document.removeEventListener('visibilitychange', handleVisibility);
      stop();
    };
  }, [refreshSession]);

  useEffect(() => {
    let cancelled = false;
    let authenticated = false;

    function applySession(me: Awaited<ReturnType<typeof getMe>>) {
      authenticated = true;
      setUser({
        userId: me.id,
        email: me.email,
        username: me.username,
        roles: me.roles,
      });
      localStorage.setItem('ragbase_user_id', me.id);
      window.dispatchEvent(new CustomEvent('auth:login'));
    }

    async function restoreSession(): Promise<boolean> {
      const me = await getMe();
      if (!cancelled && me) {
        applySession(me);
        void mergeGuest();
        return true;
      }
      return false;
    }

    async function refreshAndRestore(): Promise<void> {
      try {
        await refreshAccessToken();
        const me = await getMe();
        if (!cancelled && me) {
          applySession(me);
          void mergeGuest();
        } else if (!cancelled) {
          // Refresh returned 200 but getMe still fails (e.g. Secure cookie was
          // dropped by the http client) — do NOT keep the ghost login where the
          // UI shows a user while every request runs anonymous (silent fallback
          // to the default key). Force a real login.
          window.dispatchEvent(new CustomEvent('auth:unauthorized'));
        }
      } catch (err) {
        // Refresh failed. 401/403 = refresh_token 已过期（会话真正失效）→ 登出，
        // 避免"幽灵登录"（UI 显示 admin、业务请求却 anonymous 报"配置 API Key"）。
        // 网络错误不登出（由定时器重试）。
        const status = (err as { response?: { status?: number } })?.response
          ?.status;
        if (status === 401 || status === 403) {
          window.dispatchEvent(new CustomEvent('auth:unauthorized'));
        }
      }
    }

    async function init() {
      try {
        // B: identity restore and auth config run in parallel — a slow config
        // request must not block showing the signed-in user on refresh.
        const [config, restored] = await Promise.all([
          getAuthConfig().catch(() => null),
          (async () => {
            try {
              return await restoreSession();
            } catch {
              return false;
            }
          })(),
        ]);
        if (cancelled) return;
        const isLegacy = !config?.enabled || config?.mode === 'legacy';
        setLegacyMode(isLegacy);

        if (!restored) {
          if (isLegacy) {
            setLoading(false);
            return;
          }
          // Access token may be expired — try refreshing before giving up
          await refreshAndRestore();
        }
      } catch {
        // Auth config unavailable
      } finally {
        if (!cancelled) {
          setLoading(false);
          if (!authenticated) {
            clearLocalConversations();
          }
        }
      }
    }
    void init();

    return () => {
      cancelled = true;
    };
  }, []);

  const isAuthenticated = user !== null;

  const login = useCallback(
    async (email: string, password: string, rememberMe?: boolean) => {
      const res = await apiLogin(email, password, rememberMe);
      setLoading(false);
      setUser({
        userId: res.user.id,
        email: res.user.email,
        username: res.user.username,
        roles: res.user.roles,
      });
      localStorage.setItem('ragbase_user_id', res.user.id);
      window.dispatchEvent(new CustomEvent('auth:login'));
      void mergeGuest();
    },
    [],
  );

  const register = useCallback(
    async (email: string, code: string, password: string) => {
      const res = await apiRegister(email, code, password);
      setLoading(false);
      setUser({
        userId: res.user.id,
        email: res.user.email,
        username: res.user.username,
        roles: res.user.roles,
      });
      localStorage.setItem('ragbase_user_id', res.user.id);
      window.dispatchEvent(new CustomEvent('auth:login'));
      void mergeGuest();
    },
    [],
  );

  const verify = useCallback(async (email: string, code: string) => {
    const res = await apiVerify(email, code);
    setLoading(false);
    setUser({
      userId: res.user.id,
      email: res.user.email,
      username: res.user.username,
      roles: res.user.roles,
    });
    localStorage.setItem('ragbase_user_id', res.user.id);
    window.dispatchEvent(new CustomEvent('auth:login'));
    void mergeGuest();
  }, []);

  const forgotPassword = useCallback(async (email: string) => {
    await apiForgotPassword(email);
  }, []);

  const resetPassword = useCallback(
    async (email: string, code: string, newPassword: string) => {
      await apiResetPassword(email, code, newPassword);
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      // Invalidate server-side refresh_token cookie (httpOnly); local state clears either way.
      await apiLogout();
    } catch {
      // access_token may already be expired — the refresh cookie expires server-side on next refresh attempt.
    }
    setUser(null);
    clearLocalConversations();
    localStorage.removeItem('ragbase_user_id');
    localStorage.removeItem('ragbase-selected-model');
    localStorage.removeItem('ragbase-recent-models');
    useChatStore.getState().reset();
    setLoginModalOpen(true);
    window.dispatchEvent(new CustomEvent('auth:logout'));
  }, []);

  const resendVerification = useCallback(async (email: string) => {
    await apiResendVerification(email);
  }, []);

  const sendRegisterCode = useCallback(async (email: string) => {
    const res = await apiSendRegisterCode(email);
    return { emailHint: res.email_hint };
  }, []);

  const openLoginModal = useCallback((view?: AuthModalView) => {
    setLoginModalView(view || 'login');
    setLoginModalOpen(true);
  }, []);

  const closeLoginModal = useCallback(() => {
    setLoginModalOpen(false);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        legacyMode,
        isAuthenticated,
        loginModalOpen,
        loginModalView,
        loginModalEmail,
        login,
        register,
        verify,
        forgotPassword,
        resetPassword,
        logout,
        resendVerification,
        sendRegisterCode,
        openLoginModal,
        closeLoginModal,
        setLoginModalEmail,
        setLoginModalView,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
