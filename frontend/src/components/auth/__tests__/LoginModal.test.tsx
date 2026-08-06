import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import LoginModal from '@/components/auth/LoginModal';
import { type AuthModalView } from '@/components/auth/AuthContext';

const mockUseAuth = {
  loginModalView: 'login' as AuthModalView,
  login: vi.fn().mockResolvedValue(undefined),
  register: vi.fn().mockResolvedValue(undefined),
  forgotPassword: vi.fn().mockResolvedValue(undefined),
  resetPassword: vi.fn().mockResolvedValue(undefined),
  sendRegisterCode: vi.fn().mockResolvedValue({ emailHint: 't***@example.com' }),
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
    fireEvent.change(screen.getByPlaceholderText('邮箱地址'), { target: { value: 'user@test.com' } });
    fireEvent.change(screen.getByPlaceholderText('密码'), { target: { value: 'pass123' } });
    const form = document.querySelector('form')!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(mockUseAuth.login).toHaveBeenCalledWith('user@test.com', 'pass123');
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
    fireEvent.change(screen.getByPlaceholderText('邮箱地址'), { target: { value: 'user@test.com' } });
    const form = document.querySelector('form')!;
    fireEvent.submit(form);
    expect(await screen.findByText('请输入密码')).toBeInTheDocument();
  });

  it('shows login error from API', async () => {
    mockUseAuth.login.mockRejectedValueOnce(new Error('Invalid credentials'));
    render(<LoginModal onClose={onClose} />);
    fireEvent.change(screen.getByPlaceholderText('邮箱地址'), { target: { value: 'user@test.com' } });
    fireEvent.change(screen.getByPlaceholderText('密码'), { target: { value: 'pass123' } });
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
    expect(screen.getByText('输入注册邮箱，我们将发送验证码')).toBeInTheDocument();
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
});
