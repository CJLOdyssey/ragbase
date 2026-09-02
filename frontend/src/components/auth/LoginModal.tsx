import { useEffect, useState, type FormEvent } from 'react';
import { Loader2, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth, type AuthModalView } from './AuthContext';
import ForgotPasswordForm from './ForgotPasswordForm';
import { LoginFormFields, RegisterFormFields } from './LoginFormFields';

interface Props {
  onClose: () => void;
}

export default function LoginModal({ onClose }: Props) {
  const { t } = useTranslation();
  const {
    loginModalView: view,
    login,
    register,
    forgotPassword,
    resetPassword,
    sendRegisterCode,
    setLoginModalView: setView,
    setLoginModalEmail: setEmail,
    closeLoginModal,
  } = useAuth();

  const [email, setLocalEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [code, setCode] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [codeCooldown, setCodeCooldown] = useState(0);
  const [passwordTouched, setPasswordTouched] = useState(false);
  const [focusedField, setFocusedField] = useState<string | null>(null);
  const tabs: { key: AuthModalView; label: string }[] = [
    { key: 'login', label: t('auth.login') },
    { key: 'register', label: t('auth.register') },
  ];

  function switchView(v: AuthModalView) {
    setError('');
    setPassword('');
    setConfirmPassword('');
    setCode('');
    setCodeCooldown(0);
    setPasswordTouched(false);
    setView(v);
  }

  async function handleSendCode() {
    if (!email) {
      setError(t('auth.enterEmailFirst'));
      return;
    }
    if (codeCooldown > 0) return;
    setError('');
    setSubmitting(true);
    try {
      await sendRegisterCode(email);
      setCodeCooldown(60);
    } catch (err: unknown) {
      setError((err as { message?: string })?.message || t('auth.sendFailed'));
    } finally {
      setSubmitting(false);
    }
  }

  // 验证码倒计时：interval 生命周期绑定组件，卸载即清理
  // （原实现内联 setInterval，切换 tab/关闭弹窗后定时器泄漏并
  // 在已卸载组件上 setState）。
  useEffect(() => {
    if (codeCooldown <= 0) return;
    const id = setInterval(() => {
      setCodeCooldown((c) => (c <= 1 ? 0 : c - 1));
    }, 1000);
    return () => clearInterval(id);
  }, [codeCooldown > 0]);

  async function handleRegister() {
    setError('');
    if (!password) {
      setError(t('auth.enterPassword'));
      return;
    }
    if (password !== confirmPassword) {
      setError(t('auth.passwordMismatch'));
      return;
    }
    if (!email) {
      setError(t('auth.enterEmail'));
      return;
    }
    if (!code) {
      setError(t('auth.enterCode'));
      return;
    }
    setSubmitting(true);
    try {
      await register(email, code, password);
      closeLoginModal();
    } catch (err: unknown) {
      setError(
        (err as { message?: string })?.message || t('auth.registerFailed'),
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLogin() {
    setError('');
    if (!email) {
      setError(t('auth.enterEmail'));
      return;
    }
    if (!password) {
      setError(t('auth.enterPassword'));
      return;
    }
    setSubmitting(true);
    try {
      await login(email, password);
      closeLoginModal();
    } catch (err: unknown) {
      setError((err as { message?: string })?.message || t('auth.loginFailed'));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (view === 'register') {
      await handleRegister();
    } else {
      await handleLogin();
    }
  }

  if (view === 'forgot' || view === 'reset') {
    return (
      <div
        className="fixed inset-0 bg-[var(--color-overlay)] flex items-center justify-center z-[var(--z-modal-backdrop)] backdrop-blur-[4px]"
        onClick={onClose}
        style={{ animation: 'fadeIn 0.15s ease' }}
      >
        <div
          className="bg-[var(--color-surface-raised)] rounded-xl w-[90%] max-w-[400px] h-auto max-h-[85vh] flex flex-col [box-shadow:var(--shadow-lg)] z-[var(--z-modal)] p-0 overflow-hidden pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-center relative px-6 py-4 border-b border-[var(--color-border)]">
            <h3 className="m-0 text-lg font-bold">{t('auth.resetPassword')}</h3>
            <button
              className="bg-transparent border-none text-[var(--color-text-muted)] cursor-pointer p-1 flex items-center justify-center rounded-md transition-[background,color] duration-150 hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
              onClick={onClose}
              aria-label={t('common.close')}
              style={{
                position: 'absolute',
                right: 16,
                top: '50%',
                transform: 'translateY(-50%)',
              }}
            >
              <X size={18} />
            </button>
          </div>
          <div className="p-6 overflow-y-auto flex-1 min-h-0 flex flex-col">
            <ForgotPasswordForm
              onSendCode={async (email) => {
                await forgotPassword(email);
                setEmail(email);
              }}
              onReset={async (email, code, newPassword) => {
                await resetPassword(email, code, newPassword);
                switchView('login');
              }}
              onBack={() => switchView('login')}
              error={error}
            />
          </div>
        </div>
      </div>
    );
  }

  const isRegister = view === 'register';

  return (
    <div
      className="fixed inset-0 bg-[var(--color-overlay)] flex items-center justify-center z-[var(--z-modal-backdrop)] backdrop-blur-[4px]"
      onClick={onClose}
      style={{ animation: 'fadeIn 0.15s ease' }}
    >
      <div
        className="bg-[var(--color-surface-raised)] rounded-xl w-[90%] max-w-[400px] h-auto max-h-[85vh] flex flex-col [box-shadow:var(--shadow-lg)] z-[var(--z-modal)] p-0 overflow-hidden rounded-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="text-center pt-[28px] pb-1">
          <span className="text-xl font-bold tracking-tight text-[var(--color-text-primary)]">
            ✦ RagBase
          </span>
        </div>
        <div className="flex gap-1 mx-6 mt-4 mb-0 bg-[var(--color-surface-overlay)] rounded-[var(--radius-card)] p-[3px]">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => switchView(t.key)}
              className="flex-1 py-2 border-none rounded-[var(--radius-btn)] text-sm cursor-pointer transition-all duration-200"
              style={{
                background:
                  view === t.key
                    ? 'var(--color-surface-raised)'
                    : 'transparent',
                color:
                  view === t.key
                    ? 'var(--color-text-primary)'
                    : 'var(--color-text-tertiary)',
                fontWeight: view === t.key ? 600 : 400,
                boxShadow: view === t.key ? 'var(--shadow-sm)' : 'none',
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="px-6 pt-5 pb-6 overflow-y-auto flex-1 min-h-0 flex flex-col">
          <form onSubmit={handleSubmit}>
            {isRegister ? (
              <RegisterFormFields
                email={email}
                onEmailChange={setLocalEmail}
                password={password}
                onPasswordChange={setPassword}
                confirmPassword={confirmPassword}
                onConfirmPasswordChange={setConfirmPassword}
                code={code}
                onCodeChange={(v) => setCode(v.replace(/\D/g, '').slice(0, 6))}
                showPassword={showPassword}
                onToggleShowPassword={() => setShowPassword(!showPassword)}
                passwordTouched={passwordTouched}
                onPasswordBlur={() => {
                  setFocusedField(null);
                  setPasswordTouched(true);
                }}
                codeCooldown={codeCooldown}
                onSendCode={handleSendCode}
                submitting={submitting}
                focusedField={focusedField}
                onFocusField={setFocusedField}
                onBlurField={() => setFocusedField(null)}
              />
            ) : (
              <LoginFormFields
                email={email}
                onEmailChange={setLocalEmail}
                password={password}
                onPasswordChange={setPassword}
                showPassword={showPassword}
                onToggleShowPassword={() => setShowPassword(!showPassword)}
                focusedField={focusedField}
                onFocusField={setFocusedField}
                onBlurField={() => setFocusedField(null)}
              />
            )}

            {error && (
              <div className="px-3 py-2 rounded-[var(--radius-btn)] text-[var(--color-danger)] text-sm mb-3 leading-snug bg-[color-mix(in_srgb,var(--color-danger)_10%,_transparent)]">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-[11px] rounded-[var(--radius-btn)] border-none text-white text-base font-semibold flex items-center justify-center gap-2 transition-all duration-150"
              style={{
                background: submitting
                  ? 'var(--color-border)'
                  : 'var(--color-accent)',
                color: submitting ? 'var(--color-text-tertiary)' : '#fff',
                cursor: submitting ? 'default' : 'pointer',
              }}
              onMouseEnter={(e) => {
                if (!submitting)
                  (e.target as HTMLElement).style.opacity = '0.9';
              }}
              onMouseLeave={(e) => {
                if (!submitting) (e.target as HTMLElement).style.opacity = '1';
              }}
            >
              {submitting && (
                <Loader2
                  size={16}
                  style={{ animation: 'spin 1s linear infinite' }}
                />
              )}
              {isRegister ? t('auth.register') : t('auth.login')}
            </button>
          </form>

          {!isRegister && (
            <button
              type="button"
              onClick={() => switchView('forgot')}
              className="block mx-auto mt-3.5 bg-transparent border-none text-[var(--color-text-tertiary)] cursor-pointer text-sm p-0 transition-colors duration-150"
              onMouseEnter={(e) =>
                ((e.target as HTMLElement).style.color = 'var(--color-accent)')
              }
              onMouseLeave={(e) =>
                ((e.target as HTMLElement).style.color =
                  'var(--color-text-tertiary)')
              }
            >
              {t('auth.forgotPassword')}
            </button>
          )}

          {/* Divider + social login (reserved) */}
          {!isRegister && (
            <div className="mt-5">
              <div className="flex items-center gap-3">
                <div className="flex-1 h-px bg-[var(--color-border)]" />
                <span className="text-xs text-[var(--color-text-tertiary)] shrink-0">
                  {t('auth.or')}
                </span>
                <div className="flex-1 h-px bg-[var(--color-border)]" />
              </div>
              <div className="flex justify-center gap-3 mt-3.5">
                {[
                  { label: 'QQ', color: '#07c160' },
                  { label: t('auth.wechat'), color: '#07c160' },
                ].map((p) => (
                  <button
                    key={p.label}
                    type="button"
                    disabled
                    className="w-11 h-11 rounded-full border border-[var(--color-border)] bg-[var(--color-surface-raised)] text-[var(--color-text-tertiary)] text-xs font-semibold cursor-not-allowed opacity-40 transition-all duration-200"
                    title={t('auth.socialLoginTitle', { label: p.label })}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
