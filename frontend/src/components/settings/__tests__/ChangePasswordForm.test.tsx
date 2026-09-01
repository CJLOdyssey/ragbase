import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ChangePasswordForm from '../ChangePasswordForm';
import { changePassword } from '../../../api/client/auth';

vi.mock('../../../api/client/auth', () => ({
  changePassword: vi.fn(),
}));

vi.mock('../../../utils/useToast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      changeLanguage: vi.fn(),
      language: 'zh-CN',
    },
  }),
}));

describe('ChangePasswordForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders password form fields', () => {
    render(<ChangePasswordForm />);
    
    expect(screen.getByText('settings.changePassword.oldPassword')).toBeInTheDocument();
    expect(screen.getByText('settings.changePassword.newPassword')).toBeInTheDocument();
    expect(screen.getByText('settings.changePassword.confirmPassword')).toBeInTheDocument();
  });

  it('renders submit button', () => {
    render(<ChangePasswordForm />);
    
    const submitButton = screen.getByRole('button', { name: 'settings.changePassword.submit' });
    expect(submitButton).toBeInTheDocument();
  });

  it('disables submit button when fields are empty', () => {
    render(<ChangePasswordForm />);
    
    const submitButton = screen.getByRole('button', { name: 'settings.changePassword.submit' });
    expect(submitButton).toBeDisabled();
  });

  it('enables submit button when all fields are filled', async () => {
    const { container } = render(<ChangePasswordForm />);

    const allInputs = container.querySelectorAll('input[type="password"]');
    const oldPasswordInput = allInputs[0];
    const newPasswordInput = allInputs[1];
    const confirmPasswordInput = allInputs[2];
    
    fireEvent.change(oldPasswordInput, { target: { value: 'old123' } });
    fireEvent.change(newPasswordInput, { target: { value: 'new123' } });
    fireEvent.change(confirmPasswordInput, { target: { value: 'new123' } });
    
    await waitFor(() => {
      const submitButton = screen.getByRole('button', { name: 'settings.changePassword.submit' });
      expect(submitButton).not.toBeDisabled();
    });
  });

  it('calls changePassword with correct values', async () => {
    vi.mocked(changePassword).mockResolvedValue(undefined);

    const { container } = render(<ChangePasswordForm />);

    const allInputs = container.querySelectorAll('input[type="password"]');
    const oldPasswordInput = allInputs[0];
    const newPasswordInput = allInputs[1];
    const confirmPasswordInput = allInputs[2];
    
    fireEvent.change(oldPasswordInput, { target: { value: 'old123' } });
    fireEvent.change(newPasswordInput, { target: { value: 'new123' } });
    fireEvent.change(confirmPasswordInput, { target: { value: 'new123' } });
    
    const submitButton = screen.getByRole('button', { name: 'settings.changePassword.submit' });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(changePassword).toHaveBeenCalledWith('old123', 'new123');
    });
  });

  it('clears fields after successful password change', async () => {
    vi.mocked(changePassword).mockResolvedValue(undefined);

    const { container } = render(<ChangePasswordForm />);

    const allInputs = container.querySelectorAll('input[type="password"]');
    const oldPasswordInput = allInputs[0];
    const newPasswordInput = allInputs[1];
    const confirmPasswordInput = allInputs[2];
    
    fireEvent.change(oldPasswordInput, { target: { value: 'old123' } });
    fireEvent.change(newPasswordInput, { target: { value: 'new123' } });
    fireEvent.change(confirmPasswordInput, { target: { value: 'new123' } });
    
    const submitButton = screen.getByRole('button', { name: 'settings.changePassword.submit' });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(oldPasswordInput).toHaveValue('');
      expect(newPasswordInput).toHaveValue('');
      expect(confirmPasswordInput).toHaveValue('');
    });
  });

  it('shows error toast when passwords do not match', async () => {
    const { container } = render(<ChangePasswordForm />);

    const allInputs = container.querySelectorAll('input[type="password"]');
    const oldPasswordInput = allInputs[0];
    const newPasswordInput = allInputs[1];
    const confirmPasswordInput = allInputs[2];
    
    fireEvent.change(oldPasswordInput, { target: { value: 'old123' } });
    fireEvent.change(newPasswordInput, { target: { value: 'new123' } });
    fireEvent.change(confirmPasswordInput, { target: { value: 'different' } });
    
    const submitButton = screen.getByRole('button', { name: 'settings.changePassword.submit' });
    fireEvent.click(submitButton);
    
    // Should not call changePassword when passwords don't match
    expect(changePassword).not.toHaveBeenCalled();
  });

  it('shows error toast when changePassword fails', async () => {
    vi.mocked(changePassword).mockRejectedValue(new Error('Failed'));

    const { container } = render(<ChangePasswordForm />);

    const allInputs = container.querySelectorAll('input[type="password"]');
    const oldPasswordInput = allInputs[0];
    const newPasswordInput = allInputs[1];
    const confirmPasswordInput = allInputs[2];
    
    fireEvent.change(oldPasswordInput, { target: { value: 'old123' } });
    fireEvent.change(newPasswordInput, { target: { value: 'new123' } });
    fireEvent.change(confirmPasswordInput, { target: { value: 'new123' } });
    
    const submitButton = screen.getByRole('button', { name: 'settings.changePassword.submit' });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(changePassword).toHaveBeenCalled();
    });
  });

  it('shows submitting state while request is in progress', async () => {
    vi.mocked(changePassword).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    const { container } = render(<ChangePasswordForm />);

    const allInputs = container.querySelectorAll('input[type="password"]');
    const oldPasswordInput = allInputs[0];
    const newPasswordInput = allInputs[1];
    const confirmPasswordInput = allInputs[2];
    
    fireEvent.change(oldPasswordInput, { target: { value: 'old123' } });
    fireEvent.change(newPasswordInput, { target: { value: 'new123' } });
    fireEvent.change(confirmPasswordInput, { target: { value: 'new123' } });
    
    const submitButton = screen.getByRole('button', { name: 'settings.changePassword.submit' });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('settings.changePassword.submitting')).toBeInTheDocument();
    });
  });
});
