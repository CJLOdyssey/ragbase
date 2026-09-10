import { useState, type FormEvent } from 'react';
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
      setError('请先输入邮箱');
      return;
    }
    setError('');
    try {
      await sendCode(email);
    } catch (err: unknown) {
      setError((err as { message?: string })?.message || '发送失败');
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!password) {
      setError('请输入密码');
      return;
    }
    if (password !== confirmPassword) {
      setError('两次密码输入不一致');
      return;
    }
    if (!email) {
      setError('请输入邮箱');
      return;
    }
    if (!code) {
      setError('请输入验证码');
      return;
    }
    if (!agreed) {
      setError('请同意用户协议与隐私政策');
      return;
    }
    setError('');
    setSubmitting(true);
    try {
      await register(email, code, password);
      closeLoginModal();
    } catch (err: unknown) {
      setError((err as { message?: string })?.message || '注册失败');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    /* 与登录同构：AuthTwoColumn 左栏扫码 + 分隔线 + 右栏表单，仅字段不同 */
    <AuthTwoColumn>
      <h4 className="mb-[21px] text-[14px] font-medium text-[#c8c8d2]">
        邮箱注册
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
        <PasswordField
          value={confirmPassword}
          onChange={setConfirmPassword}
          placeholder="确认密码"
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
          注册即代表已阅读并同意{' '}
          <a href="#" className="text-[#6f9bff] hover:underline">
            用户协议
          </a>{' '}
          与{' '}
          <a href="#" className="text-[#6f9bff] hover:underline">
            隐私政策
          </a>
        </Agreement>
        <SubmitButton submitting={submitting} label="注册" />
      </form>
    </AuthTwoColumn>
  );
}
