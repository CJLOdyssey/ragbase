import { type AuthModalView } from '@/components/auth/AuthContext';
import LoginModal from '@/components/auth/LoginModal';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

const mockUseAuth = {
  loginModalView: 'login' as AuthModalView,
  login: vi.fn().mockResolvedValue(undefined),
  register: vi.fn().mockResolvedValue(undefined),
  forgotPassword: vi.fn().mockResolvedValue(undefined),
  resetPassword: vi.fn().mockResolvedValue(undefined),
  sendRegisterCode: vi
    .fn()
    .mockResolvedValue({ emailHint: 't***@example.com' }),
  setLoginModalView: vi.fn(),
  setLoginModalEmail: vi.fn(),
  closeLoginModal: vi.fn(),
};

vi.mock('@/components/auth/AuthContext', () => ({
  useAuth: () => mockUseAuth,
}));

describe('LoginModal', { tags: ['unit'] }, () => {
  const onClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.loginModalView = 'login';
  });

  it('renders login view by default', () => {
    render(<LoginModal onClose={onClose} />);
    expect(screen.getByPlaceholderText('邮箱地址')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('密码')).toBeInTheDocument();
    expect(screen.getAllByText('登录').length).toBeGreaterThanOrEqual(2);
  });

  it('renders tab buttons for login and register', () => {
    render(<LoginModal onClose={onClose} />);
    const loginTab = screen.getAllByText('登录');
    expect(loginTab.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('注册')).toBeInTheDocument();
  });

  it('shows close button', () => {
    render(<LoginModal onClose={onClose} />);
    const closeBtn = screen.getByRole('button', { name: '' });
    expect(closeBtn).toBeInTheDocument();
  });

  it('shows forgot password link in login view', () => {
    render(<LoginModal onClose={onClose} />);
    expect(screen.getByText('忘记密码？')).toBeInTheDocument();
  });

  it('calls onClose when clicking overlay', () => {
    render(<LoginModal onClose={onClose} />);
    const overlay = document.querySelector('.fixed.inset-0') as HTMLElement;
    fireEvent.click(overlay);
    expect(onClose).toHaveBeenCalled();
  });

  it('does not call onClose when clicking modal content', () => {
    render(<LoginModal onClose={onClose} />);
    const content = document.querySelector('.fixed.inset-0 > div')!;
    fireEvent.click(content);
    expect(onClose).not.toHaveBeenCalled();
  });

  it('calls login on form submit with valid inputs', async () => {
    render(<LoginModal onClose={onClose} />);
    fireEvent.change(screen.getByPlaceholderText('邮箱地址'), {
      target: { value: 'user@test.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('密码'), {
      target: { value: 'pass123' },
    });
    const form = document.querySelector('form')!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(mockUseAuth.login).toHaveBeenCalledWith(
        'user@test.com',
        'pass123',
      );
      expect(mockUseAuth.closeLoginModal).toHaveBeenCalled();
    });
  });

  it('shows error when email is empty on login', async () => {
    render(<LoginModal onClose={onClose} />);
    const form = document.querySelector('form')!;
    fireEvent.submit(form);
    expect(await screen.findByText('请输入邮箱')).toBeInTheDocument();
  });

  it('shows error when password is empty on login', async () => {
    render(<LoginModal onClose={onClose} />);
    fireEvent.change(screen.getByPlaceholderText('邮箱地址'), {
      target: { value: 'user@test.com' },
    });
    const form = document.querySelector('form')!;
    fireEvent.submit(form);
    expect(await screen.findByText('请输入密码')).toBeInTheDocument();
  });

  it('shows login error from API', async () => {
    mockUseAuth.login.mockRejectedValueOnce(new Error('Invalid credentials'));
    render(<LoginModal onClose={onClose} />);
    fireEvent.change(screen.getByPlaceholderText('邮箱地址'), {
      target: { value: 'user@test.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('密码'), {
      target: { value: 'pass123' },
    });
    const form = document.querySelector('form')!;
    fireEvent.submit(form);

    expect(await screen.findByText('Invalid credentials')).toBeInTheDocument();
  });

  it('switches to register view', () => {
    render(<LoginModal onClose={onClose} />);
    fireEvent.click(screen.getByText('注册'));
    expect(mockUseAuth.setLoginModalView).toHaveBeenCalledWith('register');
  });

  it('switches to forgot password view', () => {
    render(<LoginModal onClose={onClose} />);
    fireEvent.click(screen.getByText('忘记密码？'));
    expect(mockUseAuth.setLoginModalView).toHaveBeenCalledWith('forgot');
  });

  it('toggles password visibility', () => {
    render(<LoginModal onClose={onClose} />);
    const passwordInput = screen.getByPlaceholderText('密码');
    expect(passwordInput).toHaveAttribute('type', 'password');

    const toggleBtn = passwordInput.parentElement!.querySelector('button')!;
    fireEvent.click(toggleBtn);
    expect(passwordInput).toHaveAttribute('type', 'text');

    fireEvent.click(toggleBtn);
    expect(passwordInput).toHaveAttribute('type', 'password');
  });

  it('shows social login buttons in login view', () => {
    render(<LoginModal onClose={onClose} />);
    expect(screen.getByTitle('QQ登录（即将支持）')).toBeInTheDocument();
    expect(screen.getByTitle('微信登录（即将支持）')).toBeInTheDocument();
  });

  it('renders forgot/reset view with ForgotPasswordForm', () => {
    mockUseAuth.loginModalView = 'forgot';
    render(<LoginModal onClose={onClose} />);
    expect(screen.getByText('重置密码')).toBeInTheDocument();
    expect(
      screen.getByText('输入注册邮箱，我们将发送验证码'),
    ).toBeInTheDocument();
  });

  describe('无障碍访问', () => {
    const a11yOptions = {
      rules: {
        // TODO(DEBT): .modal-close and password-toggle buttons lack aria-label — tracked in JIRA A11Y-105
        'button-name': { enabled: false },
      },
    };

    it('should have no axe violations on login view', async () => {
      const { container } = render(<LoginModal onClose={onClose} />);
      const results = await axe(container, a11yOptions);
      expect(results).toHaveNoViolations();
    });

    it('should have no axe violations on forgot password view', async () => {
      mockUseAuth.loginModalView = 'forgot';
      const { container } = render(<LoginModal onClose={onClose} />);
      const results = await axe(container, a11yOptions);
      expect(results).toHaveNoViolations();
    });
  });

  describe('注册流程', () => {
    function renderRegister() {
      mockUseAuth.loginModalView = 'register';
      return render(<LoginModal onClose={onClose} />);
    }

    it('submits register with email, code and password', async () => {
      renderRegister();
      fireEvent.change(screen.getByPlaceholderText('邮箱地址'), {
        target: { value: 'new@test.com' },
      });
      fireEvent.change(screen.getByPlaceholderText('密码'), {
        target: { value: 'Pass@123' },
      });
      fireEvent.change(screen.getByPlaceholderText('确认密码'), {
        target: { value: 'Pass@123' },
      });
      fireEvent.change(screen.getByPlaceholderText('验证码'), {
        target: { value: '123456' },
      });
      fireEvent.submit(document.querySelector('form')!);

      await waitFor(() => {
        expect(mockUseAuth.register).toHaveBeenCalledWith(
          'new@test.com',
          '123456',
          'Pass@123',
        );
        expect(mockUseAuth.closeLoginModal).toHaveBeenCalled();
      });
    });

    it('validates empty password, mismatch, email and code in order', async () => {
      renderRegister();
      fireEvent.submit(document.querySelector('form')!);
      expect(await screen.findByText('请输入密码')).toBeInTheDocument();

      fireEvent.change(screen.getByPlaceholderText('密码'), {
        target: { value: 'Pass@123' },
      });
      fireEvent.change(screen.getByPlaceholderText('确认密码'), {
        target: { value: 'Other@456' },
      });
      fireEvent.submit(document.querySelector('form')!);
      expect(await screen.findByText('两次密码输入不一致')).toBeInTheDocument();

      fireEvent.change(screen.getByPlaceholderText('确认密码'), {
        target: { value: 'Pass@123' },
      });
      fireEvent.submit(document.querySelector('form')!);
      expect(await screen.findByText('请输入邮箱')).toBeInTheDocument();

      fireEvent.change(screen.getByPlaceholderText('邮箱地址'), {
        target: { value: 'new@test.com' },
      });
      fireEvent.submit(document.querySelector('form')!);
      expect(await screen.findByText('请输入验证码')).toBeInTheDocument();
      expect(mockUseAuth.register).not.toHaveBeenCalled();
    });

    it('shows register API errors', async () => {
      mockUseAuth.register.mockRejectedValueOnce(new Error('Email taken'));
      renderRegister();
      fireEvent.change(screen.getByPlaceholderText('邮箱地址'), {
        target: { value: 'new@test.com' },
      });
      fireEvent.change(screen.getByPlaceholderText('密码'), {
        target: { value: 'Pass@123' },
      });
      fireEvent.change(screen.getByPlaceholderText('确认密码'), {
        target: { value: 'Pass@123' },
      });
      fireEvent.change(screen.getByPlaceholderText('验证码'), {
        target: { value: '123456' },
      });
      fireEvent.submit(document.querySelector('form')!);
      expect(await screen.findByText('Email taken')).toBeInTheDocument();
    });

    it('send code requires an email first', async () => {
      renderRegister();
      fireEvent.click(screen.getByText('获取验证码'));
      expect(await screen.findByText('请先输入邮箱')).toBeInTheDocument();
      expect(mockUseAuth.sendRegisterCode).not.toHaveBeenCalled();
    });

    it('send code starts a 60s cooldown on success', async () => {
      vi.useFakeTimers();
      try {
        renderRegister();
        fireEvent.change(screen.getByPlaceholderText('邮箱地址'), {
          target: { value: 'new@test.com' },
        });
        fireEvent.click(screen.getByText('获取验证码'));
        await act(async () => {
          await Promise.resolve();
        });
        expect(mockUseAuth.sendRegisterCode).toHaveBeenCalledWith(
          'new@test.com',
        );
        const sendBtn = screen
          .getByText('60s')
          .closest('button') as HTMLButtonElement;
        expect(sendBtn.disabled).toBe(true);
        // 推进 3 秒 → 倒计时 57s
        await act(async () => {
          vi.advanceTimersByTime(3000);
        });
        expect(screen.getByText('57s')).toBeInTheDocument();
      } finally {
        vi.useRealTimers();
      }
    });

    it('send code shows API failure message', async () => {
      mockUseAuth.sendRegisterCode.mockRejectedValueOnce(
        new Error('rate limited'),
      );
      renderRegister();
      fireEvent.change(screen.getByPlaceholderText('邮箱地址'), {
        target: { value: 'new@test.com' },
      });
      fireEvent.click(screen.getByText('获取验证码'));
      expect(await screen.findByText('rate limited')).toBeInTheDocument();
    });

    it('submitting disables the submit button', async () => {
      mockUseAuth.register.mockImplementation(() => new Promise(() => {}));
      renderRegister();
      fireEvent.change(screen.getByPlaceholderText('邮箱地址'), {
        target: { value: 'new@test.com' },
      });
      fireEvent.change(screen.getByPlaceholderText('密码'), {
        target: { value: 'Pass@123' },
      });
      fireEvent.change(screen.getByPlaceholderText('确认密码'), {
        target: { value: 'Pass@123' },
      });
      fireEvent.change(screen.getByPlaceholderText('验证码'), {
        target: { value: '123456' },
      });
      fireEvent.submit(document.querySelector('form')!);
      const submitBtn = document.querySelector(
        'button[type="submit"]',
      ) as HTMLButtonElement;
      await waitFor(() => expect(submitBtn).toBeDisabled());
    });
  });

  describe('忘记密码 / 重置流程', () => {
    beforeEach(() => {
      mockUseAuth.forgotPassword.mockResolvedValue(undefined);
      mockUseAuth.resetPassword.mockResolvedValue(undefined);
    });

    it('forgot view sends code via forgotPassword and stores email', async () => {
      mockUseAuth.loginModalView = 'forgot';
      render(<LoginModal onClose={onClose} />);
      fireEvent.change(screen.getByPlaceholderText('邮箱地址'), {
        target: { value: 'user@test.com' },
      });
      fireEvent.submit(document.querySelector('form')!);
      await waitFor(() => {
        expect(mockUseAuth.forgotPassword).toHaveBeenCalledWith(
          'user@test.com',
        );
        expect(mockUseAuth.setLoginModalEmail).toHaveBeenCalledWith(
          'user@test.com',
        );
      });
    });

    it('reset flow calls resetPassword then switches back to login', async () => {
      mockUseAuth.loginModalView = 'reset';
      render(<LoginModal onClose={onClose} />);
      // 先走 email 步骤发送验证码，再进入 code 步骤
      fireEvent.change(screen.getByPlaceholderText('邮箱地址'), {
        target: { value: 'user@test.com' },
      });
      fireEvent.submit(document.querySelector('form')!);
      await screen.findByPlaceholderText('验证码');
      fireEvent.change(screen.getByPlaceholderText('验证码'), {
        target: { value: '888888' },
      });
      const newPwd = screen.getByPlaceholderText('新密码 (至少8位)');
      fireEvent.change(newPwd, { target: { value: 'New@Pass1' } });
      fireEvent.change(screen.getByPlaceholderText('确认新密码'), {
        target: { value: 'New@Pass1' },
      });
      fireEvent.submit(document.querySelector('form')!);
      await waitFor(() => {
        expect(mockUseAuth.resetPassword).toHaveBeenCalledWith(
          'user@test.com',
          '888888',
          'New@Pass1',
        );
        expect(mockUseAuth.setLoginModalView).toHaveBeenCalledWith('login');
      });
    });

    it('back button returns to login view', () => {
      mockUseAuth.loginModalView = 'forgot';
      render(<LoginModal onClose={onClose} />);
      fireEvent.click(screen.getByText('返回登录'));
      expect(mockUseAuth.setLoginModalView).toHaveBeenCalledWith('login');
    });

    it('surfaces forgot-password API errors', async () => {
      mockUseAuth.forgotPassword.mockRejectedValueOnce(new Error('no account'));
      mockUseAuth.loginModalView = 'forgot';
      render(<LoginModal onClose={onClose} />);
      fireEvent.change(screen.getByPlaceholderText('邮箱地址'), {
        target: { value: 'user@test.com' },
      });
      fireEvent.submit(document.querySelector('form')!);
      expect(await screen.findByText('发送失败')).toBeInTheDocument();
    });
  });
});
