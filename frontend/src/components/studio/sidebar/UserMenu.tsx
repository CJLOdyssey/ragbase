import { useCallback, useEffect, useRef } from 'react';
import type * as React from 'react';
import { useIsMobile } from '../../../hooks/useMediaQuery';
import { useAuth } from '../../auth/AuthContext';
import ActionSheet, { type ActionSheetItem } from '../../shared/ActionSheet';
import { HelpCircle, Key, LogIn, LogOut, Settings, User } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface Props {
  isUserMenuOpen: boolean;
  setIsUserMenuOpen: (v: boolean) => void;
  setIsSettingsOpen: (v: boolean) => void;
  setIsApiOpen: (v: boolean) => void;
}

function PopoverItem({
  icon,
  label,
  disabled = false,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  disabled?: boolean;
  onClick: () => void;
}) {
  const { t } = useTranslation();
  return (
    <button
      className={`flex items-center gap-3 w-full px-3 py-2.5 bg-transparent border-none rounded-md text-[var(--color-text-secondary)] text-base cursor-pointer transition-[color,background] duration-150 text-left hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]${disabled ? ' opacity-40 cursor-not-allowed hover:text-[var(--color-text-secondary)] hover:bg-transparent' : ''}`}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      title={disabled ? t('user.loginToManage') : undefined}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

function UserAvatar({
  authLoading,
  isAuthenticated,
  user,
}: {
  authLoading: boolean;
  isAuthenticated: boolean;
  user: { username?: string | null; email?: string } | null;
}) {
  if (authLoading) {
    return (
      <div className="w-5 h-5 rounded-full bg-[var(--color-surface-hover)] animate-pulse" />
    );
  }
  if (isAuthenticated && user?.username) {
    return (
      <span className="text-sm font-semibold text-[var(--color-accent)] leading-none">
        {user.username.charAt(0).toUpperCase()}
      </span>
    );
  }
  return <User size={18} className="text-[var(--color-text-secondary)]" />;
}

function UserName({
  authLoading,
  isAuthenticated,
  user,
}: {
  authLoading: boolean;
  isAuthenticated: boolean;
  user: { username?: string | null; email?: string } | null;
}) {
  const { t } = useTranslation();
  if (authLoading) {
    return (
      <span className="inline-block h-4 w-16 rounded bg-[var(--color-surface-hover)] animate-pulse align-middle" />
    );
  }
  if (isAuthenticated) {
    return <>{user?.username || user?.email}</>;
  }
  return <>{t('user.guest')}</>;
}

function UserStatus({
  authLoading,
  isAuthenticated,
}: {
  authLoading: boolean;
  isAuthenticated: boolean;
}) {
  const { t } = useTranslation();
  if (authLoading) {
    return (
      <span className="inline-block h-3 w-20 rounded bg-[var(--color-surface-hover)] animate-pulse align-middle" />
    );
  }
  return (
    <>
      <span className="w-2 h-2 rounded-full bg-[var(--color-success)]" />
      {isAuthenticated ? t('user.onlineStatus') : t('user.notLoggedIn')}
    </>
  );
}

function buildActionItems({
  isAuthenticated,
  handleItemClick,
  closeMenu,
  setIsApiOpen,
  setIsSettingsOpen,
  logout,
  openLoginModal,
  t,
}: {
  isAuthenticated: boolean;
  handleItemClick: (action: () => void) => void;
  closeMenu: () => void;
  setIsApiOpen: (v: boolean) => void;
  setIsSettingsOpen: (v: boolean) => void;
  logout: () => void;
  openLoginModal: () => void;
  t: (key: string) => string;
}): ActionSheetItem[] {
  const authItem: ActionSheetItem = isAuthenticated
    ? {
        key: 'logout',
        icon: <LogOut size={16} />,
        label: t('sidebar.logout'),
        onClick: () => handleItemClick(logout),
      }
    : {
        key: 'login',
        icon: <LogIn size={16} />,
        label: t('user.loginRegister'),
        onClick: () => handleItemClick(() => openLoginModal()),
      };

  return [
    {
      key: 'api',
      icon: <Key size={16} />,
      label: 'API',
      onClick: () => handleItemClick(() => setIsApiOpen(true)),
    },
    {
      key: 'settings',
      icon: <Settings size={16} />,
      label: t('sidebar.settings'),
      onClick: () => handleItemClick(() => setIsSettingsOpen(true)),
    },
    {
      key: 'help',
      icon: <HelpCircle size={16} />,
      label: t('sidebar.help'),
      onClick: () => closeMenu(),
    },
    authItem,
  ];
}

export default function UserMenu({
  isUserMenuOpen,
  setIsUserMenuOpen,
  setIsSettingsOpen,
  setIsApiOpen,
}: Props) {
  const { t } = useTranslation();
  const {
    user,
    isAuthenticated,
    loading: authLoading,
    logout,
    openLoginModal,
  } = useAuth();
  const menuRef = useRef<HTMLDivElement>(null);
  const isMobile = useIsMobile();

  const closeMenu = useCallback(
    () => setIsUserMenuOpen(false),
    [setIsUserMenuOpen],
  );

  useEffect(() => {
    if (!isUserMenuOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeMenu();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isUserMenuOpen, closeMenu]);

  useEffect(() => {
    if (!isUserMenuOpen || isMobile) return;
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        closeMenu();
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [isUserMenuOpen, closeMenu, isMobile]);

  const handleItemClick = (action: () => void) => {
    closeMenu();
    action();
  };

  const actionItems = buildActionItems({
    isAuthenticated,
    handleItemClick,
    closeMenu,
    setIsApiOpen,
    setIsSettingsOpen,
    logout,
    openLoginModal,
    t,
  });

  return (
    <div className="shrink-0 p-4 relative" ref={menuRef}>
      {isMobile ? (
        <MobileView
          isUserMenuOpen={isUserMenuOpen}
          setIsUserMenuOpen={setIsUserMenuOpen}
          closeMenu={closeMenu}
          actionItems={actionItems}
          authLoading={authLoading}
          isAuthenticated={isAuthenticated}
          user={user}
        />
      ) : (
        <DesktopView
          isUserMenuOpen={isUserMenuOpen}
          setIsUserMenuOpen={setIsUserMenuOpen}
          closeMenu={closeMenu}
          handleItemClick={handleItemClick}
          setIsApiOpen={setIsApiOpen}
          setIsSettingsOpen={setIsSettingsOpen}
          logout={logout}
          openLoginModal={openLoginModal}
          authLoading={authLoading}
          isAuthenticated={isAuthenticated}
          user={user}
          t={t}
        />
      )}
    </div>
  );
}

function MobileView({
  isUserMenuOpen,
  setIsUserMenuOpen,
  closeMenu,
  actionItems,
  authLoading,
  isAuthenticated,
  user,
}: {
  isUserMenuOpen: boolean;
  setIsUserMenuOpen: (v: boolean) => void;
  closeMenu: () => void;
  actionItems: ActionSheetItem[];
  authLoading: boolean;
  isAuthenticated: boolean;
  user: { username?: string | null; email?: string } | null;
}) {
  return (
    <>
      <button
        className="flex items-center justify-between w-full p-2.5 bg-transparent border border-transparent rounded-lg text-[var(--color-text-primary)] cursor-pointer transition-[color,background] duration-150 hover:bg-[var(--color-surface-hover)]"
        onClick={() => setIsUserMenuOpen(true)}
        aria-expanded={isUserMenuOpen}
        aria-haspopup="menu"
      >
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="w-9 h-9 bg-[var(--color-accent)]/15 rounded-full flex items-center justify-center shrink-0">
            <UserAvatar
              authLoading={authLoading}
              isAuthenticated={isAuthenticated}
              user={user}
            />
          </div>
          <div className="overflow-hidden text-left">
            <div className="text-base font-semibold text-[var(--color-text-primary)] whitespace-nowrap overflow-hidden text-ellipsis">
              <UserName
                authLoading={authLoading}
                isAuthenticated={isAuthenticated}
                user={user}
              />
            </div>
            <div className="text-sm text-[var(--color-text-secondary)] flex items-center gap-1 mt-0.5">
              <UserStatus
                authLoading={authLoading}
                isAuthenticated={isAuthenticated}
              />
            </div>
          </div>
        </div>
      </button>
      <ActionSheet
        open={isUserMenuOpen}
        onClose={closeMenu}
        items={actionItems}
      />
    </>
  );
}

function DesktopView({
  isUserMenuOpen,
  setIsUserMenuOpen,
  closeMenu,
  handleItemClick,
  setIsApiOpen,
  setIsSettingsOpen,
  logout,
  openLoginModal,
  authLoading,
  isAuthenticated,
  user,
  t,
}: {
  isUserMenuOpen: boolean;
  setIsUserMenuOpen: (v: boolean) => void;
  closeMenu: () => void;
  handleItemClick: (action: () => void) => void;
  setIsApiOpen: (v: boolean) => void;
  setIsSettingsOpen: (v: boolean) => void;
  logout: () => void;
  openLoginModal: () => void;
  authLoading: boolean;
  isAuthenticated: boolean;
  user: { username?: string | null; email?: string } | null;
  t: (key: string) => string;
}) {
  return (
    <>
      {isUserMenuOpen && (
        <div className="absolute bottom-[calc(100%+8px)] left-4 right-4 bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-xl shadow-[0_4px_16px_rgba(0,0,0,0.18)] z-[var(--z-modal)] flex flex-col p-1 origin-bottom animate-[popoverScaleIn_0.15s_cubic-bezier(0.16,1,0.3,1)]">
          <PopoverItem
            icon={<Key size={16} className="w-4 h-4 mr-1" />}
            label="API"
            onClick={() => handleItemClick(() => setIsApiOpen(true))}
          />
          <PopoverItem
            icon={<Settings size={16} className="w-4 h-4 mr-1" />}
            label={t('sidebar.settings')}
            onClick={() => handleItemClick(() => setIsSettingsOpen(true))}
          />
          <PopoverItem
            icon={<HelpCircle size={16} className="w-4 h-4 mr-1" />}
            label={t('sidebar.help')}
            onClick={() => closeMenu()}
          />

          <div className="h-px bg-[var(--color-border)] my-1" />
          {isAuthenticated ? (
            <PopoverItem
              icon={<LogOut size={16} className="w-4 h-4 mr-1" />}
              label={t('sidebar.logout')}
              onClick={() => handleItemClick(logout)}
            />
          ) : (
            <button
              className="flex items-center gap-3 w-full px-3 py-2.5 bg-transparent border-none rounded-md text-[var(--color-accent)] font-semibold text-base cursor-pointer transition-[color,background] duration-150 text-left hover:text-[var(--color-accent-hover)] hover:bg-[var(--color-surface-hover)]"
              onClick={() => handleItemClick(() => openLoginModal())}
            >
              <LogIn size={16} className="w-4 h-4 mr-1" />
              <span>{t('user.loginRegister')}</span>
            </button>
          )}
        </div>
      )}

      <button
        className="flex items-center justify-between w-full p-2.5 bg-transparent border border-transparent rounded-lg text-[var(--color-text-primary)] cursor-pointer transition-[color,background] duration-150 hover:bg-[var(--color-surface-hover)]"
        onClick={() => {
          if (isUserMenuOpen) {
            closeMenu();
          } else {
            setIsUserMenuOpen(true);
          }
        }}
        aria-expanded={isUserMenuOpen}
        aria-haspopup="menu"
      >
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="w-9 h-9 bg-[var(--color-accent)]/15 rounded-full flex items-center justify-center shrink-0">
            <UserAvatar
              authLoading={authLoading}
              isAuthenticated={isAuthenticated}
              user={user}
            />
          </div>
          <div className="overflow-hidden text-left">
            <div className="text-base font-semibold text-[var(--color-text-primary)] whitespace-nowrap overflow-hidden text-ellipsis">
              <UserName
                authLoading={authLoading}
                isAuthenticated={isAuthenticated}
                user={user}
              />
            </div>
            <div className="text-sm text-[var(--color-text-secondary)] flex items-center gap-1 mt-0.5">
              <UserStatus
                authLoading={authLoading}
                isAuthenticated={isAuthenticated}
              />
            </div>
          </div>
        </div>
      </button>
    </>
  );
}
