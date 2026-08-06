import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PasswordStrengthIndicator from '@/components/auth/PasswordStrengthIndicator';

describe('PasswordStrengthIndicator', { tags: ['unit'] }, () => {
  it('renders nothing when password is empty', () => {
    const { container } = render(<PasswordStrengthIndicator password="" validated={false} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders 6 progress bars', () => {
    const { container } = render(<PasswordStrengthIndicator password="a" validated={false} />);
    const bars = container.querySelectorAll('div.h-\\[3px\\]');
    expect(bars.length).toBe(6);
  });

  it('shows failed checks when validated', () => {
    render(<PasswordStrengthIndicator password="abc" validated={true} />);
    expect(screen.getByText(/至少 8 位/)).toBeInTheDocument();
    expect(screen.getByText(/数字/)).toBeInTheDocument();
    expect(screen.getByText(/大写/)).toBeInTheDocument();
    expect(screen.getByText(/特殊字符/)).toBeInTheDocument();
  });

  it('does not show failed checks when not validated', () => {
    render(<PasswordStrengthIndicator password="abc" validated={false} />);
    expect(screen.queryByText(/至少 8 位/)).not.toBeInTheDocument();
  });

  it('shows success message when all checks pass', () => {
    render(<PasswordStrengthIndicator password="StrongP@ss1" validated={true} />);
    expect(screen.getByText(/全部满足/)).toBeInTheDocument();
  });

  it('marks short password as failing length check', () => {
    render(<PasswordStrengthIndicator password="ab" validated={true} />);
    expect(screen.getByText(/至少 8 位/)).toBeInTheDocument();
  });

  it('marks password without digits as failing digit check', () => {
    render(<PasswordStrengthIndicator password="abcdefgh" validated={true} />);
    expect(screen.getByText(/数字/)).toBeInTheDocument();
  });

  it('marks common password as failing', () => {
    render(<PasswordStrengthIndicator password="password" validated={true} />);
    expect(screen.getByText(/非常见密码/)).toBeInTheDocument();
  });
});
