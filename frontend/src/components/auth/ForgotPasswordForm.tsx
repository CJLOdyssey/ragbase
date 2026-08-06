import { useState, type FormEvent } from 'react';
import PasswordStrengthIndicator from './PasswordStrengthIndicator';

interface Props {
  onSendCode: (email: string) => Promise<void>;
  onReset: (email: string, code: string, newPassword: string) => Promise<void>;
  onBack: () => void;
  error: string;
}

type Step = 'email' | 'code' | 'reset';

const btnClass =
  'w-full py-[10px] rounded-[var(--radius-btn)] border-none bg-[var(--color-accent)] text-white text-base font-semibold';

function SubmitButton({
  submitting,
  label,
}: {
  submitting: boolean;
  label: string;
}) {
  return (
    <button
      type="submit"
      disabled={submitting}
      className={btnClass}
      style={{
        cursor: submitting ? 'default' : 'pointer',
        opacity: submitting ? 0.6 : 1,
      }}
    >
      {label}
    </button>
  );
}

export default function ForgotPasswordForm({
  onSendCode,
  onReset,
  onBack,
  error,
}: Props) {
  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [localError, setLocalError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSendCode(e: FormEvent) {
    e.preventDefault();
    if (!email) {
      setLocalError('请输入邮箱');
      return;
    }
    setSubmitting(true);
    setLocalError('');
    try {
      await onSendCode(email);
      setStep('code');
    } catch {
      setLocalError('发送失败');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReset(e: FormEvent) {
    e.preventDefault();
    if (!email || !code || !newPassword) {
      setLocalError('请填写完整信息');
      return;
    }
    if (newPassword !== confirmPassword) {
      setLocalError('两次密码输入不一致');
      return;
    }
    setSubmitting(true);
    setLocalError('');
    try {
      await onReset(email, code, newPassword);
      setStep('reset');
    } catch (err: unknown) {
      setLocalError((err as { message?: string })?.message || '重置失败');
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    'w-full px-3 py-[10px] rounded-[var(--radius-btn)] border border-[var(--color-border)] bg-[var(--color-surface-raised)] text-[var(--color-text-primary)] text-sm outline-none box-border mb-3';

  const errorText = localError || error;

  if (step === 'reset') {
    return (
      <div className="text-center py-5">
        <div className="text-[40px] mb-3">✓</div>
        <p className="text-base font-semibold m-0 mb-2">密码已重置</p>
        <p className="text-sm text-[var(--color-text-tertiary)] m-0 mb-5">
          请使用新密码重新登录
        </p>
        <button
          onClick={onBack}
          className={btnClass}
          style={{
            cursor: submitting ? 'default' : 'pointer',
            opacity: submitting ? 0.6 : 1,
          }}
        >
          返回登录
        </button>
      </div>
    );
  }

  if (step === 'code') {
    return (
      <form onSubmit={handleReset}>
        <p className="text-sm text-[var(--color-text-tertiary)] mb-4">
          验证码已发送至 {email}
        </p>
        <input
          type="text"
          inputMode="numeric"
          placeholder="验证码"
          value={code}
          onChange={(e) => setCode(e.target.value.slice(0, 6))}
          className={inputClass}
          autoComplete="one-time-code"
        />
        <input
          type="password"
          placeholder="新密码 (至少8位)"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          className={inputClass}
        />
        <PasswordStrengthIndicator password={newPassword} validated={true} />
        <input
          type="password"
          placeholder="确认新密码"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          className={`${inputClass} mt-3`}
        />
        {errorText && (
          <p className="m-0 mb-2 text-sm text-[var(--color-danger)]">
            {errorText}
          </p>
        )}
        <SubmitButton
          submitting={submitting}
          label={submitting ? '重置中...' : '重置密码'}
        />
        <button
          type="button"
          onClick={() => setStep('email')}
          className="block mx-auto mt-3 bg-transparent border-none text-[var(--color-text-tertiary)] cursor-pointer text-sm underline"
        >
          返回
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={handleSendCode}>
      <p className="text-sm text-[var(--color-text-tertiary)] mb-4">
        输入注册邮箱，我们将发送验证码
      </p>
      <input
        type="email"
        placeholder="邮箱地址"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className={inputClass}
        autoComplete="email"
      />
      {errorText && (
        <p className="m-0 mb-2 text-sm text-[var(--color-danger)]">
          {errorText}
        </p>
      )}
      <SubmitButton
        submitting={submitting}
        label={submitting ? '发送中...' : '发送验证码'}
      />
      <button
        type="button"
        onClick={onBack}
        className="block mx-auto mt-3 bg-transparent border-none text-[var(--color-text-tertiary)] cursor-pointer text-sm underline"
      >
        返回登录
      </button>
    </form>
  );
}
