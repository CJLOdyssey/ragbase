import { useState } from 'react';
import { Input, Select } from 'antd';
import { Mail, Send } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import MobileModal from '../shared/MobileModal';

export type InviteRole = 'admin' | 'member';

export interface InviteUserModalProps {
  submitting?: boolean;
  onClose: () => void;
  onInvite: (email: string, role: InviteRole) => void;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function InviteUserModal({
  submitting = false,
  onClose,
  onInvite,
}: InviteUserModalProps) {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<InviteRole>('member');
  const [emailError, setEmailError] = useState<string | null>(null);

  const handleSubmit = () => {
    if (!email || !EMAIL_RE.test(email)) {
      setEmailError(t('admin.invite.emailInvalid'));
      return;
    }
    setEmailError(null);
    onInvite(email.trim(), role);
  };

  return (
    <MobileModal
      open={true}
      onClose={onClose}
      mode="sheet"
      title={t('admin.invite.title')}
      width={460}
      footer={
        <>
          <button
            onClick={onClose}
            className="h-9 px-4 rounded-[9px] border border-[var(--color-border)] bg-transparent text-[13px] text-[var(--color-text-secondary)] cursor-pointer hover:text-[var(--color-text-primary)] transition-colors"
          >
            {t('admin.invite.cancel')}
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="h-9 px-4 rounded-[9px] border-none text-white text-[13px] font-medium cursor-pointer inline-flex items-center gap-1.5 bg-[linear-gradient(135deg,var(--color-accent),var(--color-accent-hover))] shadow-[0_2px_10px_color-mix(in_srgb,var(--color-accent)_28%,transparent)] hover:shadow-[0_4px_18px_color-mix(in_srgb,var(--color-accent)_45%,transparent)] transition-all disabled:opacity-60"
          >
            <Send size={14} />
            {t('admin.invite.send')}
          </button>
        </>
      }
    >
      <div className="flex flex-col gap-4 py-1">
        <div className="flex flex-col gap-1.5">
          <label className="text-[12.5px] font-medium text-[var(--color-text-secondary)]">
            {t('admin.invite.emailLabel')}
          </label>
          <div className="relative">
            <Mail
              size={14}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]"
            />
            <Input
              size="large"
              placeholder="user@example.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (emailError) setEmailError(null);
              }}
              status={emailError ? 'error' : undefined}
              className="!pl-9"
            />
          </div>
          {emailError && (
            <span className="text-[12px] text-[var(--color-danger)]">
              {emailError}
            </span>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-[12.5px] font-medium text-[var(--color-text-secondary)]">
            {t('admin.invite.role')}
          </label>
          <Select<InviteRole>
            size="large"
            value={role}
            onChange={setRole}
            options={[
              {
                value: 'member',
                label: `member — ${t('admin.invite.memberDesc')}`,
              },
              {
                value: 'admin',
                label: `admin — ${t('admin.invite.adminDesc')}`,
              },
            ]}
          />
        </div>
      </div>
    </MobileModal>
  );
}
