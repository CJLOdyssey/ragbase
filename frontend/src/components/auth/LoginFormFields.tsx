import type * as React from 'react';
import { Mail, Lock, Eye, EyeOff, ShieldCheck } from 'lucide-react';
import PasswordStrengthIndicator from './PasswordStrengthIndicator';

const inputBase = 'w-full pl-9 pr-10 py-[10px] rounded-[var(--radius-btn)] border border-[var(--color-border)] bg-[var(--color-surface-raised)] text-[var(--color-text-primary)] text-sm outline-none box-border transition-[border-color,box-shadow] duration-200';

const iconBase: React.CSSProperties = {
  position: 'absolute',
  left: 10,
  top: '50%',
  transform: 'translateY(-50%)',
  pointerEvents: 'none',
  color: 'var(--color-text-tertiary)',
  width: 16,
  height: 16,
};

const eyeToggleStyle: React.CSSProperties = {
  position: 'absolute',
  right: 10,
  top: '50%',
  transform: 'translateY(-50%)',
  background: 'none',
  border: 'none',
  color: 'var(--color-text-tertiary)',
  cursor: 'pointer',
  padding: 0,
  display: 'flex',
};

function dynamicStyle(focusedField: string | null, field: string): React.CSSProperties {
  return {
    borderColor: focusedField === field ? 'var(--color-accent)' : 'var(--color-border)',
    boxShadow: focusedField === field ? '0 0 0 2px color-mix(in srgb, var(--color-accent) 20%, transparent)' : 'none',
  };
}

interface FieldCallbacks {
  focusedField: string | null;
  onFocusField: (field: string) => void;
  onBlurField: () => void;
}

interface EmailFieldProps extends FieldCallbacks {
  value: string;
  onChange: (value: string) => void;
}

function EmailField({ value, onChange, focusedField, onFocusField, onBlurField }: EmailFieldProps) {
  return (
    <div className="relative mb-3.5">
      <Mail style={iconBase} size={16} />
      <input
        type="email"
        placeholder="邮箱地址"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => onFocusField('email')}
        onBlur={onBlurField}
        className={inputBase}
        style={dynamicStyle(focusedField, 'email')}
        autoComplete="email"
      />
    </div>
  );
}

interface PasswordFieldProps extends FieldCallbacks {
  value: string;
  onChange: (value: string) => void;
  showPassword: boolean;
  onToggleShowPassword: () => void;
  wrapperClass: string;
  autoComplete: string;
  hint?: React.ReactNode;
}

function PasswordField({ value, onChange, showPassword, onToggleShowPassword, wrapperClass, autoComplete, hint, focusedField, onFocusField, onBlurField }: PasswordFieldProps) {
  return (
    <div className={wrapperClass}>
      <div className="relative">
        <Lock style={iconBase} size={16} />
        <input
          type={showPassword ? 'text' : 'password'}
          placeholder="密码"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => onFocusField('password')}
          onBlur={onBlurField}
          className={inputBase}
          style={dynamicStyle(focusedField, 'password')}
          autoComplete={autoComplete}
        />
        <button
          type="button"
          onClick={onToggleShowPassword}
          style={eyeToggleStyle}
          tabIndex={-1}
        >
          {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
      {hint}
    </div>
  );
}

interface ConfirmPasswordFieldProps extends FieldCallbacks {
  value: string;
  onChange: (value: string) => void;
  showPassword: boolean;
  password: string;
  passwordTouched: boolean;
}

function ConfirmPasswordField({ value, onChange, showPassword, password, passwordTouched, focusedField, onFocusField, onBlurField }: ConfirmPasswordFieldProps) {
  return (
    <div className="relative mb-4">
      <Lock style={iconBase} size={16} />
      <input
        type={showPassword ? 'text' : 'password'}
        placeholder="确认密码"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => onFocusField('confirm')}
        onBlur={onBlurField}
        className={inputBase}
        style={dynamicStyle(focusedField, 'confirm')}
        autoComplete="new-password"
      />
      {value && passwordTouched && value !== password && (
        <div className="text-xs text-[var(--color-danger)] mt-1">
          ○ 与密码不一致
        </div>
      )}
    </div>
  );
}

interface CodeFieldRowProps extends FieldCallbacks {
  value: string;
  onChange: (value: string) => void;
  codeCooldown: number;
  onSendCode: () => void;
  disabled: boolean;
}

function CodeFieldRow({ value, onChange, codeCooldown, onSendCode, disabled, focusedField, onFocusField, onBlurField }: CodeFieldRowProps) {
  return (
    <div className="flex gap-2 items-start mb-3">
      <div className="relative flex-1">
        <ShieldCheck style={iconBase} size={16} />
        <input
          type="text"
          inputMode="numeric"
          placeholder="验证码"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => onFocusField('code')}
          onBlur={onBlurField}
          className={inputBase}
          style={dynamicStyle(focusedField, 'code')}
          autoComplete="one-time-code"
        />
      </div>
      <button
        type="button"
        onClick={onSendCode}
        disabled={disabled || codeCooldown > 0}
        className="h-10 px-3.5 rounded-[var(--radius-btn)] border text-xs font-semibold whitespace-nowrap shrink-0 transition-all duration-200"
        style={{
          borderColor: codeCooldown > 0 ? 'var(--color-border)' : 'var(--color-accent)',
          background: codeCooldown > 0 ? 'var(--color-surface-raised)' : 'transparent',
          color: codeCooldown > 0 ? 'var(--color-text-tertiary)' : 'var(--color-accent)',
          cursor: codeCooldown > 0 ? 'default' : 'pointer',
        }}
      >
        {codeCooldown > 0 ? `${codeCooldown}s` : '获取验证码'}
      </button>
    </div>
  );
}

export interface LoginFormFieldsProps extends FieldCallbacks {
  email: string;
  onEmailChange: (value: string) => void;
  password: string;
  onPasswordChange: (value: string) => void;
  showPassword: boolean;
  onToggleShowPassword: () => void;
}

export function LoginFormFields({ email, onEmailChange, password, onPasswordChange, showPassword, onToggleShowPassword, focusedField, onFocusField, onBlurField }: LoginFormFieldsProps) {
  return (
    <>
      <EmailField
        value={email}
        onChange={onEmailChange}
        focusedField={focusedField}
        onFocusField={onFocusField}
        onBlurField={onBlurField}
      />
      <PasswordField
        value={password}
        onChange={onPasswordChange}
        focusedField={focusedField}
        onFocusField={onFocusField}
        onBlurField={onBlurField}
        showPassword={showPassword}
        onToggleShowPassword={onToggleShowPassword}
        wrapperClass="relative mb-3.5"
        autoComplete="current-password"
      />
    </>
  );
}

export interface RegisterFormFieldsProps extends FieldCallbacks {
  email: string;
  onEmailChange: (value: string) => void;
  password: string;
  onPasswordChange: (value: string) => void;
  confirmPassword: string;
  onConfirmPasswordChange: (value: string) => void;
  code: string;
  onCodeChange: (value: string) => void;
  showPassword: boolean;
  onToggleShowPassword: () => void;
  passwordTouched: boolean;
  onPasswordBlur: () => void;
  codeCooldown: number;
  onSendCode: () => void;
  submitting: boolean;
}

export function RegisterFormFields({
  email, onEmailChange, password, onPasswordChange, confirmPassword, onConfirmPasswordChange,
  code, onCodeChange, showPassword, onToggleShowPassword, passwordTouched, onPasswordBlur,
  codeCooldown, onSendCode, submitting, focusedField, onFocusField, onBlurField,
}: RegisterFormFieldsProps) {
  return (
    <>
      <EmailField
        value={email}
        onChange={onEmailChange}
        focusedField={focusedField}
        onFocusField={onFocusField}
        onBlurField={onBlurField}
      />
      <PasswordField
        value={password}
        onChange={onPasswordChange}
        focusedField={focusedField}
        onFocusField={onFocusField}
        onBlurField={onPasswordBlur}
        showPassword={showPassword}
        onToggleShowPassword={onToggleShowPassword}
        wrapperClass="mb-4"
        autoComplete="new-password"
        hint={password && !passwordTouched && (
          <div className="text-xs text-[var(--color-text-tertiary)] mt-1 opacity-60">
            至少8位 · 数字 · 小写 · 大写 · 特殊字符
          </div>
        )}
      />
      <ConfirmPasswordField
        value={confirmPassword}
        onChange={onConfirmPasswordChange}
        focusedField={focusedField}
        onFocusField={onFocusField}
        onBlurField={onPasswordBlur}
        showPassword={showPassword}
        password={password}
        passwordTouched={passwordTouched}
      />
      <PasswordStrengthIndicator password={password} validated={passwordTouched} />
      <CodeFieldRow
        value={code}
        onChange={onCodeChange}
        focusedField={focusedField}
        onFocusField={onFocusField}
        onBlurField={onBlurField}
        codeCooldown={codeCooldown}
        onSendCode={onSendCode}
        disabled={submitting}
      />
    </>
  );
}
