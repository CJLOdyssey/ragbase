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
  refreshTokens,
} from '../../api/client/auth';
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
    try {
      await refreshTokens();
      lastRefreshRef.current = Date.now();
      return true;
    } catch {
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
    window.addEventListener('auth:login', start);
    window.addEventListener('auth:logout', stop);
    window.addEventListener('auth:unauthorized', stop);
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      window.removeEventListener('auth:login', start);
      window.removeEventListener('auth:logout', stop);
      window.removeEventListener('auth:unauthorized', stop);
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
        await refreshTokens();
        const me = await getMe();
        if (!cancelled && me) {
          applySession(me);
          void mergeGuest();
        }
      } catch {
        // Refresh failed — guest stays
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
    useChatStore.getState().reset();
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
