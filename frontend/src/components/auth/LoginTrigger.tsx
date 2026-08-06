import { LogOut, Settings } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

export default function LoginTrigger() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { isAuthenticated, user, openLoginModal, logout } = useAuth();

  return (
    <div className="fixed top-4 right-4 z-50 flex items-center gap-2">
      {isAuthenticated ? (
        <>
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
        </>
      ) : (
        <>
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
        </>
      )}
      <button
        type="button"
        onClick={() => navigate('/settings')}
        aria-label={t('settings.settings')}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-surface-raised)] border border-[var(--color-border)] text-[var(--color-text-primary)] cursor-pointer hover:bg-[var(--color-surface-hover)]"
      >
        <Settings size={14} />
      </button>
    </div>
  );
}
