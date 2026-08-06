import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ForgotPasswordForm from '@/components/auth/ForgotPasswordForm';

describe('ForgotPasswordForm', { tags: ['unit'] }, () => {
  const defaultProps = {
    onSendCode: vi.fn().mockResolvedValue(undefined),
    onReset: vi.fn().mockResolvedValue(undefined),
    onBack: vi.fn(),
    error: '',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders email step by default', () => {
    render(<ForgotPasswordForm {...defaultProps} />);
    expect(screen.getByPlaceholderText('邮箱地址')).toBeInTheDocument();
    expect(screen.getByText('发送验证码')).toBeInTheDocument();
    expect(screen.getByText('返回登录')).toBeInTheDocument();
  });

  it('shows local error when submitting empty email', async () => {
    render(<ForgotPasswordForm {...defaultProps} />);
    fireEvent.click(screen.getByText('发送验证码'));
    expect(await screen.findByText('请输入邮箱')).toBeInTheDocument();
  });

  it('calls onSendCode with email', async () => {
    render(<ForgotPasswordForm {...defaultProps} />);
    fireEvent.change(screen.getByPlaceholderText('邮箱地址'), { target: { value: 'test@example.com' } });
    fireEvent.click(screen.getByText('发送验证码'));
    await waitFor(() => {
      expect(defaultProps.onSendCode).toHaveBeenCalledWith('test@example.com');
    });
  });

  it('transitions to code step after successful send', async () => {
    render(<ForgotPasswordForm {...defaultProps} />);
    fireEvent.change(screen.getByPlaceholderText('邮箱地址'), { target: { value: 'test@example.com' } });
    fireEvent.click(screen.getByText('发送验证码'));
    await waitFor(() => {
      expect(screen.getByText(/验证码已发送至 test@example.com/)).toBeInTheDocument();
    });
  });

  it('shows local error when onSendCode fails', async () => {
    const onSendCode = vi.fn().mockRejectedValue(new Error('fail'));
    render(<ForgotPasswordForm {...defaultProps} onSendCode={onSendCode} />);
    fireEvent.change(screen.getByPlaceholderText('邮箱地址'), { target: { value: 'test@example.com' } });
    fireEvent.click(screen.getByText('发送验证码'));
    expect(await screen.findByText('发送失败')).toBeInTheDocument();
  });

  it('shows password mismatch error on reset step', async () => {
    const onSendCode = vi.fn().mockResolvedValue(undefined);
    render(<ForgotPasswordForm {...defaultProps} onSendCode={onSendCode} />);

    fireEvent.change(screen.getByPlaceholderText('邮箱地址'), { target: { value: 'test@example.com' } });
    fireEvent.click(screen.getByText('发送验证码'));
    await screen.findByText(/验证码已发送/);

    fireEvent.change(screen.getByPlaceholderText('验证码'), { target: { value: '123456' } });
    fireEvent.change(screen.getByPlaceholderText('新密码 (至少8位)'), { target: { value: 'NewPass1!' } });
    fireEvent.change(screen.getByPlaceholderText('确认新密码'), { target: { value: 'DifferentPass1!' } });
    fireEvent.click(screen.getByText('重置密码'));

    expect(await screen.findByText('两次密码输入不一致')).toBeInTheDocument();
  });

  it('calls onReset with correct params on valid reset', async () => {
    const onSendCode = vi.fn().mockResolvedValue(undefined);
    render(<ForgotPasswordForm {...defaultProps} onSendCode={onSendCode} />);

    fireEvent.change(screen.getByPlaceholderText('邮箱地址'), { target: { value: 'test@example.com' } });
    fireEvent.click(screen.getByText('发送验证码'));
    await screen.findByText(/验证码已发送/);

    fireEvent.change(screen.getByPlaceholderText('验证码'), { target: { value: '123456' } });
    fireEvent.change(screen.getByPlaceholderText('新密码 (至少8位)'), { target: { value: 'NewPass1!' } });
    fireEvent.change(screen.getByPlaceholderText('确认新密码'), { target: { value: 'NewPass1!' } });
    fireEvent.click(screen.getByText('重置密码'));

    await waitFor(() => {
      expect(defaultProps.onReset).toHaveBeenCalledWith('test@example.com', '123456', 'NewPass1!');
    });
  });

  it('shows success step after reset', async () => {
    const onSendCode = vi.fn().mockResolvedValue(undefined);
    render(<ForgotPasswordForm {...defaultProps} onSendCode={onSendCode} />);

    fireEvent.change(screen.getByPlaceholderText('邮箱地址'), { target: { value: 'test@example.com' } });
    fireEvent.click(screen.getByText('发送验证码'));
    await screen.findByText(/验证码已发送/);

    fireEvent.change(screen.getByPlaceholderText('验证码'), { target: { value: '123456' } });
    fireEvent.change(screen.getByPlaceholderText('新密码 (至少8位)'), { target: { value: 'NewPass1!' } });
    fireEvent.change(screen.getByPlaceholderText('确认新密码'), { target: { value: 'NewPass1!' } });
    fireEvent.click(screen.getByText('重置密码'));

    await waitFor(() => {
      expect(screen.getByText('密码已重置')).toBeInTheDocument();
      expect(screen.getByText('返回登录')).toBeInTheDocument();
    });
  });

  it('calls onBack when clicking back button on email step', () => {
    render(<ForgotPasswordForm {...defaultProps} />);
    fireEvent.click(screen.getByText('返回登录'));
    expect(defaultProps.onBack).toHaveBeenCalled();
  });

  it('displays external error prop', () => {
    render(<ForgotPasswordForm {...defaultProps} error="Server error" />);
    expect(screen.getByText('Server error')).toBeInTheDocument();
  });
});
