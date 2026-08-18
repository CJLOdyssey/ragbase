import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { changePassword } from '../../api/client/auth';
import { useToast } from '../../utils/useToast';

export default function ChangePasswordForm() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!oldPassword || !newPassword) return;
    if (newPassword !== confirmPassword) {
      toast(t('settings.changePassword.mismatch'), 'error');
      return;
    }
    setSubmitting(true);
    try {
      await changePassword(oldPassword, newPassword);
      toast(t('settings.changePassword.success'), 'success');
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : t('settings.changePassword.failed');
      toast(msg, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 max-w-[360px]">
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-[var(--color-text-primary)]">
          {t('settings.changePassword.oldPassword')}
        </label>
        <input
          type="password"
          className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
          value={oldPassword}
          onChange={(e) => setOldPassword(e.target.value)}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-[var(--color-text-primary)]">
          {t('settings.changePassword.newPassword')}
        </label>
        <input
          type="password"
          className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-[var(--color-text-primary)]">
          {t('settings.changePassword.confirmPassword')}
        </label>
        <input
          type="password"
          className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
        />
      </div>
      <button
        className="self-start px-4 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-accent)] text-white hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
        onClick={handleSubmit}
        disabled={submitting || !oldPassword || !newPassword}
      >
        {submitting
          ? t('settings.changePassword.submitting')
          : t('settings.changePassword.submit')}
      </button>
    </div>
  );
}
