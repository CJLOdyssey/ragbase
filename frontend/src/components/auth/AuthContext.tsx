import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import {
  forgotPassword as apiForgotPassword,
  login as apiLogin,
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
    localStorage.removeItem('agentstudio-conversations');
    window.dispatchEvent(new Event('agentstudio-conversations-updated'));
  } catch {}
}

async function mergeGuest() {
  try {
    const guestId = localStorage.getItem('agentstudio_user_id');
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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [legacyMode, setLegacyMode] = useState(true);
  const [loading, setLoading] = useState(true);
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [loginModalView, setLoginModalView] = useState<AuthModalView>('login');
  const [loginModalEmail, setLoginModalEmail] = useState('');

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
      localStorage.setItem('agentstudio_user_id', me.id);
      window.dispatchEvent(new CustomEvent('auth:login'));
    }

    async function restoreSession(): Promise<boolean> {
      const me = await getMe();
      if (!cancelled && me) {
        applySession(me);
        await mergeGuest();
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
          await mergeGuest();
        }
      } catch {
        // Refresh failed — guest stays
      }
    }

    async function init() {
      try {
        const config = await getAuthConfig();
        if (cancelled) return;
        const isLegacy = !config.enabled || config.mode === 'legacy';
        setLegacyMode(isLegacy);

        // Tokens are httpOnly cookies — axios withCredentials carries them.
        try {
          await restoreSession();
        } catch {
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
      localStorage.setItem('agentstudio_user_id', res.user.id);
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
      localStorage.setItem('agentstudio_user_id', res.user.id);
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
    localStorage.setItem('agentstudio_user_id', res.user.id);
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
    setUser(null);
    clearLocalConversations();
    localStorage.removeItem('agentstudio_user_id');
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
