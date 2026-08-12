import { LoginFormFields, RegisterFormFields } from '../LoginFormFields';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

function loginProps(overrides: Record<string, unknown> = {}) {
  return {
    email: '',
    onEmailChange: vi.fn(),
    password: '',
    onPasswordChange: vi.fn(),
    showPassword: false,
    onToggleShowPassword: vi.fn(),
    focusedField: null as string | null,
    onFocusField: vi.fn(),
    onBlurField: vi.fn(),
    ...overrides,
  };
}

describe('LoginFormFields', { tags: ['unit'] }, () => {
  it('renders email and password inputs with placeholders', () => {
    render(<LoginFormFields {...loginProps()} />);
    expect(
      screen.getByPlaceholderText('auth.emailPlaceholder'),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText('auth.passwordPlaceholder'),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText('auth.passwordPlaceholder'),
    ).toHaveAttribute('type', 'password');
    expect(
      screen.getByPlaceholderText('auth.emailPlaceholder'),
    ).toHaveAttribute('type', 'email');
  });

  it('toggles password visibility via the eye button', () => {
    const props = loginProps();
    render(<LoginFormFields {...props} />);
    const input = screen.getByPlaceholderText('auth.passwordPlaceholder');
    const toggle = input.parentElement!.querySelector('button')!;
    fireEvent.click(toggle);
    expect(props.onToggleShowPassword).toHaveBeenCalled();
  });

  it('reflects showPassword on the input type', () => {
    render(<LoginFormFields {...loginProps({ showPassword: true })} />);
    expect(
      screen.getByPlaceholderText('auth.passwordPlaceholder'),
    ).toHaveAttribute('type', 'text');
  });

  it('focus/blur callbacks propagate with field names', () => {
    const props = loginProps();
    render(<LoginFormFields {...props} />);
    fireEvent.focus(screen.getByPlaceholderText('auth.emailPlaceholder'));
    expect(props.onFocusField).toHaveBeenCalledWith('email');
    fireEvent.blur(screen.getByPlaceholderText('auth.emailPlaceholder'));
    expect(props.onBlurField).toHaveBeenCalled();
    fireEvent.focus(screen.getByPlaceholderText('auth.passwordPlaceholder'));
    expect(props.onFocusField).toHaveBeenCalledWith('password');
  });

  it('applies accent border style when a field is focused', () => {
    render(<LoginFormFields {...loginProps({ focusedField: 'email' })} />);
    const input = screen.getByPlaceholderText('auth.emailPlaceholder');
    expect(input.style.borderColor).toBe('var(--color-accent)');
  });
});

function registerProps(overrides: Record<string, unknown> = {}) {
  return {
    email: '',
    onEmailChange: vi.fn(),
    password: '',
    onPasswordChange: vi.fn(),
    confirmPassword: '',
    onConfirmPasswordChange: vi.fn(),
    code: '',
    onCodeChange: vi.fn(),
    showPassword: false,
    onToggleShowPassword: vi.fn(),
    passwordTouched: false,
    onPasswordBlur: vi.fn(),
    codeCooldown: 0,
    onSendCode: vi.fn(),
    submitting: false,
    focusedField: null as string | null,
    onFocusField: vi.fn(),
    onBlurField: vi.fn(),
    ...overrides,
  };
}

describe('RegisterFormFields', { tags: ['unit'] }, () => {
  it('renders confirm/code fields and the strength indicator', () => {
    render(<RegisterFormFields {...registerProps()} />);
    expect(
      screen.getByPlaceholderText('auth.confirmPasswordPlaceholder'),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText('auth.codePlaceholder'),
    ).toBeInTheDocument();
    expect(screen.getByText('auth.sendCode')).toBeInTheDocument();
  });

  it('shows the mismatch hint once touched and values differ', () => {
    render(
      <RegisterFormFields
        {...registerProps({
          password: 'abc',
          confirmPassword: 'abd',
          passwordTouched: true,
        })}
      />,
    );
    expect(screen.getByText('auth.mismatch')).toBeInTheDocument();
  });

  it('no mismatch hint when untouched or matching', () => {
    const { rerender } = render(
      <RegisterFormFields
        {...registerProps({ password: 'abc', confirmPassword: 'abd' })}
      />,
    );
    expect(screen.queryByText('auth.mismatch')).toBeNull();
    rerender(
      <RegisterFormFields
        {...registerProps({
          password: 'abc',
          confirmPassword: 'abc',
          passwordTouched: true,
        })}
      />,
    );
    expect(screen.queryByText('auth.mismatch')).toBeNull();
  });

  it('shows the password hint before touch', () => {
    render(<RegisterFormFields {...registerProps({ password: 'abc' })} />);
    expect(screen.getByText('auth.passwordHint')).toBeInTheDocument();
  });

  it('hides the password hint after touch', () => {
    render(
      <RegisterFormFields
        {...registerProps({ password: 'abc', passwordTouched: true })}
      />,
    );
    expect(screen.queryByText('auth.passwordHint')).toBeNull();
  });

  it('renders cooldown seconds and disables the send button during cooldown', () => {
    render(<RegisterFormFields {...registerProps({ codeCooldown: 45 })} />);
    const sendBtn = screen
      .getByText('45s')
      .closest('button') as HTMLButtonElement;
    expect(sendBtn.disabled).toBe(true);
  });

  it('disables the send button while submitting', () => {
    render(<RegisterFormFields {...registerProps({ submitting: true })} />);
    const sendBtn = screen
      .getByText('auth.sendCode')
      .closest('button') as HTMLButtonElement;
    expect(sendBtn.disabled).toBe(true);
  });

  it('send code button fires onSendCode', () => {
    const props = registerProps();
    render(<RegisterFormFields {...props} />);
    fireEvent.click(screen.getByText('auth.sendCode'));
    expect(props.onSendCode).toHaveBeenCalled();
  });

  it('password blur marks touched', () => {
    const props = registerProps();
    render(<RegisterFormFields {...props} />);
    fireEvent.blur(screen.getByPlaceholderText('auth.passwordPlaceholder'));
    expect(props.onPasswordBlur).toHaveBeenCalled();
  });
});
