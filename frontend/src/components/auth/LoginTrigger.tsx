import { LogOut } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from './AuthContext';

export default function LoginTrigger() {
  const { t } = useTranslation();
  const { isAuthenticated, user, openLoginModal, logout } = useAuth();

  if (isAuthenticated) {
    return (
      <div className="fixed top-4 right-4 z-50 flex items-center gap-2">
        <span className="text-sm text-[var(--color-text-muted)]">
          {user?.username || user?.email}
        </span>
        <button
          type="button"
          onClick={() => void logout()}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-surface-raised)] border border-[var(--color-border)] text-[var(--color-text-primary)] cursor-pointer hover:bg-[var(--color-surface-hover)]"
        >
          <LogOut size={14} />
          {t('auth.logout')}
        </button>
      </div>
    );
  }

  return (
    <div className="fixed top-4 right-4 z-50 flex gap-2">
      <button
        type="button"
        onClick={() => openLoginModal('register')}
        className="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-surface-raised)] border border-[var(--color-border)] text-[var(--color-text-primary)] cursor-pointer hover:bg-[var(--color-surface-hover)]"
      >
        {t('auth.register')}
      </button>
      <button
        type="button"
        onClick={() => openLoginModal('login')}
        className="px-3 py-1.5 rounded-lg text-xs font-medium text-white cursor-pointer bg-[var(--color-accent, #4f46e5)] hover:opacity-90"
      >
        {t('auth.login')}
      </button>
    </div>
  );
}
