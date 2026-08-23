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
  register as apiRegister,
  resendVerification as apiResendVerification,
  resetPassword as apiResetPassword,
  sendRegisterCode as apiSendRegisterCode,
  verify as apiVerify,
  getMe,
} from '../../api/client/auth';
import { refreshAccessToken } from '../../api/client/refresh';
import { useChatStore } from '../../stores/chatStore';
import { getStorageManager, STORAGE_KEYS } from '../../utils/storage';

const sm = getStorageManager();

function clearLocalConversations() {
  try {
    sm.remove(STORAGE_KEYS.CONVERSATIONS);
    sm.remove(STORAGE_KEYS.SESSIONS_CACHE);
    window.dispatchEvent(new Event('ragbase-conversations-updated'));
  } catch {}
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

const REFRESH_INTERVAL_MS = 10 * 60 * 1000;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [loginModalView, setLoginModalView] = useState<AuthModalView>('login');
  const [loginModalEmail, setLoginModalEmail] = useState('');
  const refreshTimerRef = useRef<number | null>(null);
  const lastRefreshRef = useRef(0);

  const refreshSession = useCallback(async (): Promise<boolean> => {
    try {
      await refreshAccessToken();
      lastRefreshRef.current = Date.now();
      return true;
    } catch {
      return false;
    }
  }, []);

  useEffect(() => {
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

    function applySession(me: Awaited<ReturnType<typeof getMe>>) {
      setUser({
        userId: me.id,
        email: me.email,
        username: me.username,
        roles: me.roles,
      });
      sm.setUserId(me.id);
      window.dispatchEvent(new CustomEvent('auth:login'));
    }

    async function restoreSession(): Promise<boolean> {
      const me = await getMe();
      if (!cancelled && me) {
        applySession(me);
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
        }
        // getMe returned falsy → no valid session. Do NOT dispatch
        // auth:unauthorized here; errors.ts normalizeError owns that
        // responsibility for 401/403 responses on actual API calls.
      } catch {
        // refreshAccessToken failed — again, errors.ts dispatches
        // auth:unauthorized when the next API call 401s. Avoid
        // double-dispatch from AuthContext.
      }
    }

    async function init() {
      try {
        // 尝试恢复 session (JWT cookie)
        const restored = await restoreSession().catch(() => false);
        if (cancelled) return;

        if (!restored) {
          // 无有效 session — 尝试 refresh
          await refreshAndRestore();
        }
      } catch {
        // Auth config unavailable
      } finally {
        if (!cancelled) {
          setLoading(false);
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
      sm.setUserId(res.user.id);
      setLoading(false);
      setUser({
        userId: res.user.id,
        email: res.user.email,
        username: res.user.username,
        roles: res.user.roles,
      });
      window.dispatchEvent(new CustomEvent('auth:login'));
    },
    [],
  );

  const register = useCallback(
    async (email: string, code: string, password: string) => {
      const res = await apiRegister(email, code, password);
      sm.setUserId(res.user.id);
      setLoading(false);
      setUser({
        userId: res.user.id,
        email: res.user.email,
        username: res.user.username,
        roles: res.user.roles,
      });
      window.dispatchEvent(new CustomEvent('auth:login'));
    },
    [],
  );

  const verify = useCallback(async (email: string, code: string) => {
    const res = await apiVerify(email, code);
    sm.setUserId(res.user.id);
    setLoading(false);
    setUser({
      userId: res.user.id,
      email: res.user.email,
      username: res.user.username,
      roles: res.user.roles,
    });
    window.dispatchEvent(new CustomEvent('auth:login'));
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
      await apiLogout();
    } catch {
      // access_token may already be expired
    }
    setUser(null);
    sm.clearSession();
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
