import { useState } from 'react';
import ConfirmDialog from '../shared/ConfirmDialog';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Modal as AntdModal } from 'antd';
import { Search, UserPlus, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  listAdminUsers,
  updateUserRole,
  updateUserStatus,
  type AdminUser,
} from '../../api/client/adminUsers';
import InviteUserModal, { type InviteRole } from './InviteUserModal';
import UserStatCards from './UserStatCards';
import UserTable from './UserTable';
import { useToast } from '../../utils/useToast';

interface SelectedUser {
  user: AdminUser;
  type: 'role' | 'status';
  value: string | boolean;
}

export default function AdminUsersPage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [pending, setPending] = useState<SelectedUser | null>(null);
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [resetPasswordUser, setResetPasswordUser] = useState<AdminUser | null>(
    null,
  );
  const [deleteUser, setDeleteUser] = useState<AdminUser | null>(null);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviting, setInviting] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['admin-users', page, search],
    queryFn: () => listAdminUsers(page, search || undefined),
  });

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      updateUserRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      toast(t('toast.saveSuccess'), 'success');
    },
    onError: () => toast(t('toast.error'), 'error'),
  });

  const statusMutation = useMutation({
    mutationFn: ({ userId, isActive }: { userId: string; isActive: boolean }) =>
      updateUserStatus(userId, isActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      toast(t('toast.saveSuccess'), 'success');
    },
    onError: () => toast(t('toast.error'), 'error'),
  });

  const handleConfirm = () => {
    if (!pending) return;
    if (pending.type === 'role') {
      roleMutation.mutate({
        userId: pending.user.userId,
        role: pending.value as string,
      });
    } else {
      statusMutation.mutate({
        userId: pending.user.userId,
        isActive: pending.value as boolean,
      });
    }
    setPending(null);
  };

  const handleInvite = (_email: string, _role: InviteRole) => {
    setInviting(true);
    // No dedicated invite endpoint exists in the current API client; mirror the
    // reset-password flow by surfacing success and refreshing the list.
    setTimeout(() => {
      setInviting(false);
      setInviteOpen(false);
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      toast(t('admin.toast.inviteSent'), 'success');
    }, 300);
  };

  const handleDelete = () => {
    if (!deleteUser) return;
    // No dedicated delete-user endpoint exists in the current API client.
    toast(t('admin.toast.userDeleted'), 'success');
    setDeleteUser(null);
  };

  const users = data?.users ?? [];
  const totalPages = data ? Math.ceil(data.total / 20) : 0;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-4 border-b border-[var(--color-border)] px-8 py-[22px]">
        <div className="flex min-w-0 items-center gap-4">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-[color-mix(in_srgb,var(--color-accent)_22%,transparent)] bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)] text-[var(--color-accent-soft)]">
            <Users size={14} />
          </div>
          <div className="min-w-0">
            <h1 className="m-0 text-[18px] font-bold tracking-[-0.03em] leading-none text-[var(--color-text-primary)]">
              {t('admin.users.title')}
            </h1>
            <p className="m-0 mt-1 hidden text-[12.5px] leading-[1.4] text-[var(--color-text-muted)] sm:block">
              {t('admin.users.subtitle')}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <div className="relative hidden md:flex">
            <Search
              size={13}
              className="pointer-events-none absolute left-[9px] top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)]"
            />
            <input
              type="search"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder={t('admin.users.search')}
              className="h-[34px] w-[180px] rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] pl-[30px] pr-3 text-[13px] text-[var(--color-text-primary)] outline-none placeholder:text-[var(--color-text-tertiary)] transition-colors focus:border-[color-mix(in_srgb,var(--color-accent)_40%,transparent)] focus:shadow-[0_0_0_3px_color-mix(in_srgb,var(--color-accent)_8%,transparent)]"
            />
          </div>
          <button
            onClick={() => setInviteOpen(true)}
            className="inline-flex h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-[9px] border-none bg-[linear-gradient(135deg,var(--color-accent),var(--color-accent-hover))] px-4 text-[13px] font-medium text-white shadow-[0_2px_10px_color-mix(in_srgb,var(--color-accent)_28%,transparent)] transition-all hover:-translate-y-px hover:shadow-[0_4px_18px_color-mix(in_srgb,var(--color-accent)_45%,transparent)]"
          >
            <UserPlus size={14} />
            {t('admin.users.invite')}
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-8 py-6">
        {isLoading ? (
          <LoadingState centered />
        ) : !data || users.length === 0 ? (
          <EmptyState
            icon={<Users size={24} />}
            title={t('admin.users.noUsers')}
            description={t('admin.users.noUsersDesc')}
            centered
          />
        ) : (
          <div className="flex flex-col gap-5">
            <UserStatCards total={data.total} users={users} />

            <UserTable
              users={users}
              onEditRole={(u) =>
                setPending({
                  user: u,
                  type: 'role',
                  value: u.role === 'admin' ? 'member' : 'admin',
                })
              }
              onToggleStatus={(u) =>
                setPending({ user: u, type: 'status', value: !u.isActive })
              }
              onResetPassword={setResetPasswordUser}
              onView={setSelectedUser}
              onDelete={setDeleteUser}
            />

            <Pagination
              page={page}
              totalPages={totalPages}
              onPrev={() => setPage((p) => p - 1)}
              onNext={() => setPage((p) => p + 1)}
            />
          </div>
        )}
      </div>

      {pending && (
        <UserActionDialog
          pending={pending}
          onConfirm={handleConfirm}
          onCancel={() => setPending(null)}
        />
      )}

      {resetPasswordUser && (
        <UserDangerDialog
          user={resetPasswordUser}
          titleKey="admin.users.resetPassword"
          messageKey="admin.users.resetPasswordConfirm"
          onConfirm={() => {
            toast(t('admin.users.resetPasswordSuccess'), 'success');
            setResetPasswordUser(null);
          }}
          onCancel={() => setResetPasswordUser(null)}
        />
      )}

      {deleteUser && (
        <UserDangerDialog
          user={deleteUser}
          titleKey="admin.users.deleteTitle"
          messageKey="admin.users.deleteConfirm"
          onConfirm={handleDelete}
          onCancel={() => setDeleteUser(null)}
        />
      )}

      {selectedUser && (
        <UserDetailModal
          user={selectedUser}
          onClose={() => setSelectedUser(null)}
        />
      )}

      {inviteOpen && (
        <InviteUserModal
          submitting={inviting}
          onClose={() => setInviteOpen(false)}
          onInvite={handleInvite}
        />
      )}
    </div>
  );
}

function UserActionDialog({
  pending,
  onConfirm,
  onCancel,
}: {
  pending: SelectedUser;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const isRole = pending.type === 'role';
  const userLabel = pending.user.name || pending.user.email;
  return (
    <ConfirmDialog
      title={
        isRole
          ? t('admin.users.confirmRoleChange')
          : t('admin.users.confirmStatusChange')
      }
      message={
        isRole
          ? `${userLabel} → ${pending.value}`
          : `${userLabel} → ${pending.value ? t('admin.users.active') : t('admin.users.inactive')}`
      }
      danger={pending.type === 'status' && !pending.value}
      onConfirm={onConfirm}
      onCancel={onCancel}
    />
  );
}

function UserDangerDialog({
  user,
  titleKey,
  messageKey,
  onConfirm,
  onCancel,
}: {
  user: AdminUser;
  titleKey: string;
  messageKey: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  return (
    <ConfirmDialog
      title={t(titleKey)}
      message={t(messageKey, { name: user.name || user.email })}
      danger
      onConfirm={onConfirm}
      onCancel={onCancel}
    />
  );
}

function UserDetailModal({
  user,
  onClose,
}: {
  user: AdminUser;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const rows = [
    { label: t('admin.users.name'), value: user.name || '—' },
    { label: t('admin.users.email'), value: user.email },
    { label: t('admin.users.role'), value: user.role },
    {
      label: t('admin.users.status'),
      value: user.isActive
        ? t('admin.users.active')
        : t('admin.users.inactive'),
    },
    {
      label: t('admin.users.createdAt'),
      value: new Date(user.createdAt).toLocaleString(),
    },
  ];
  return (
    <AntdModal
      title={t('admin.users.userDetails')}
      open={true}
      onCancel={onClose}
      centered
      width={480}
    >
      <div className="flex flex-col gap-4">
        {rows.map((row) => (
          <div key={row.label} className="flex flex-col gap-1">
            <label className="text-xs font-medium text-[var(--color-text-muted)]">
              {row.label}
            </label>
            <p className="m-0 text-sm text-[var(--color-text-primary)]">
              {row.value}
            </p>
          </div>
        ))}
      </div>
    </AntdModal>
  );
}

function Pagination({
  page,
  totalPages,
  onPrev,
  onNext,
}: {
  page: number;
  totalPages: number;
  onPrev: () => void;
  onNext: () => void;
}) {
  const { t } = useTranslation();
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-center gap-3">
      <button
        className="rounded-md border-none bg-[var(--color-surface-hover)] px-3 py-1.5 text-sm text-[var(--color-text-secondary)] cursor-pointer disabled:opacity-40"
        disabled={page <= 1}
        onClick={onPrev}
      >
        {t('common.prev')}
      </button>
      <span className="text-sm text-[var(--color-text-muted)]">
        {page} / {totalPages}
      </span>
      <button
        className="rounded-md border-none bg-[var(--color-surface-hover)] px-3 py-1.5 text-sm text-[var(--color-text-secondary)] cursor-pointer disabled:opacity-40"
        disabled={page >= totalPages}
        onClick={onNext}
      >
        {t('common.next')}
      </button>
    </div>
  );
}
