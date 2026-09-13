import { useState, type FormEvent } from 'react';
import { useAuth } from './AuthContext';
import {
  AuthTwoColumn,
  EmailField,
  ErrorBanner,
  PasswordField,
  SubmitButton,
} from './AuthFormParts';

export default function LoginPanel() {
  const { login, closeLoginModal, setLoginModalView } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email) {
      setError('请输入邮箱');
      return;
    }
    if (!password) {
      setError('请输入密码');
      return;
    }
    setError('');
    setSubmitting(true);
    try {
      await login(email, password);
      closeLoginModal();
    } catch (err: unknown) {
      setError((err as { message?: string })?.message || '登录失败');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    /* 两栏固定结构，右栏 307：307/190 ≈ 1.62 ≈ φ */
    <AuthTwoColumn>
      <h4 className="mb-[21px] text-[14px] font-medium text-[#c8c8d2]">
        邮箱登录
      </h4>
      <form onSubmit={handleSubmit} className="space-y-[13px]">
        <EmailField value={email} onChange={setEmail} />
        <PasswordField
          value={password}
          onChange={setPassword}
          placeholder="密码"
          visible={showPassword}
          onToggleVisible={() => setShowPassword((v) => !v)}
        />
        {error && <ErrorBanner message={error} />}
        <div className="text-right">
          <button
            type="button"
            onClick={() => setLoginModalView('forgot')}
            className="bg-transparent text-[12px] text-[#8b8b9a] transition-colors hover:text-[#6f9bff]"
          >
            忘记密码？
          </button>
        </div>
        <SubmitButton submitting={submitting} label="登录" />
      </form>
    </AuthTwoColumn>
  );
}
