import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from './AuthContext';
import {
  Agreement,
  AuthTwoColumn,
  CodeField,
  EmailField,
  ErrorBanner,
  PasswordField,
  SubmitButton,
} from './AuthFormParts';
import { useVerificationCode } from './useVerificationCode';

export default function RegisterPanel() {
  const { t } = useTranslation();
  const { register, sendRegisterCode, closeLoginModal } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [code, setCode] = useState('');
  const [agreed, setAgreed] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { cooldown, sending, sendCode } = useVerificationCode(sendRegisterCode);

  async function handleSend() {
    if (!email) {
      setError(t('auth.enterEmailFirst'));
      return;
    }
    setError('');
    try {
      await sendCode(email);
    } catch (err: unknown) {
      setError((err as { message?: string })?.message || t('auth.sendFailed'));
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
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
    if (!agreed) {
      setError(t('auth.agreeRequired'));
      return;
    }
    setError('');
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

  return (
    /* 与登录同构：AuthTwoColumn 左栏扫码 + 分隔线 + 右栏表单，仅字段不同 */
    <AuthTwoColumn>
      <h4 className="mb-[21px] text-[14px] font-medium text-[#c8c8d2]">
        {t('auth.emailRegisterTitle')}
      </h4>
      <form onSubmit={handleSubmit} className="space-y-[13px]">
        <EmailField value={email} onChange={setEmail} />
        <PasswordField
          value={password}
          onChange={setPassword}
          placeholder={t('auth.passwordPlaceholder')}
          visible={showPassword}
          onToggleVisible={() => setShowPassword((v) => !v)}
        />
        <PasswordField
          value={confirmPassword}
          onChange={setConfirmPassword}
          placeholder={t('auth.confirmPasswordPlaceholder')}
          visible={showConfirm}
          onToggleVisible={() => setShowConfirm((v) => !v)}
        />
        <CodeField
          value={code}
          onChange={setCode}
          onSend={handleSend}
          cooldown={cooldown}
          sending={sending}
        />
        {error && <ErrorBanner message={error} />}
        <Agreement checked={agreed} onChange={setAgreed}>
          {t('auth.agreementPrefix')}{' '}
          <a href="#" className="text-[#6f9bff] hover:underline">
            {t('auth.termsOfService')}
          </a>{' '}
          {t('auth.and')}{' '}
          <a href="#" className="text-[#6f9bff] hover:underline">
            {t('auth.privacyPolicy')}
          </a>
        </Agreement>
        <SubmitButton submitting={submitting} label={t('auth.register')} />
      </form>
    </AuthTwoColumn>
  );
}
