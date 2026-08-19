import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Search, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import ConfirmDialog from '../shared/ConfirmDialog';
import {
  listAdminUsers,
  updateUserRole,
  updateUserStatus,
  type AdminUser,
} from '../../api/client/adminUsers';
import { useToast } from '../../utils/useToast';

interface PendingChange {
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
  const [pending, setPending] = useState<PendingChange | null>(null);

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
      roleMutation.mutate({ userId: pending.user.userId, role: pending.value as string });
    } else {
      statusMutation.mutate({ userId: pending.user.userId, isActive: pending.value as boolean });
    }
    setPending(null);
  };

  const totalPages = data ? Math.ceil(data.total / 20) : 0;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)]">
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)] m-0">
          {t('admin.users.title')}
        </h1>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 p-6">
        <div className="relative mb-4">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full pl-9 pr-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
            placeholder={t('admin.users.search')}
          />
        </div>

        {isLoading ? (
          <LoadingState />
        ) : !data || data.users.length === 0 ? (
          <EmptyState icon={<Users size={24} />} description={t('admin.users.noUsers')} />
        ) : (
          <>
            <div className="flex flex-col gap-2">
              {data.users.map((user) => (
                <div
                  key={user.userId}
                  className="flex items-center gap-4 px-4 py-3 rounded-lg bg-[var(--color-surface-raised)]"
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                      {user.name || user.email}
                    </div>
                    <div className="text-xs text-[var(--color-text-muted)] truncate">
                      {user.email}
                    </div>
                  </div>

                  <select
                    value={user.role}
                    onChange={(e) =>
                      setPending({ user, type: 'role', value: e.target.value })
                    }
                    className="px-2 py-1 rounded-md text-xs bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none cursor-pointer"
                  >
                    <option value="member">member</option>
                    <option value="admin">admin</option>
                  </select>

                  <button
                    className={`px-2 py-1 rounded-md text-xs border-none cursor-pointer ${
                      user.isActive
                        ? 'bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)] text-[var(--color-accent)]'
                        : 'bg-[color-mix(in_srgb,var(--color-danger)_12%,transparent)] text-[var(--color-danger, #dc2626)]'
                    }`}
                    onClick={() =>
                      setPending({ user, type: 'status', value: !user.isActive })
                    }
                  >
                    {user.isActive ? t('admin.users.active') : t('admin.users.inactive')}
                  </button>

                  <span className="text-xs text-[var(--color-text-muted)] shrink-0">
                    {new Date(user.createdAt).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-3 mt-6">
                <button
                  className="px-3 py-1.5 rounded-md text-sm bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] border-none cursor-pointer disabled:opacity-40"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  {t('common.prev')}
                </button>
                <span className="text-sm text-[var(--color-text-muted)]">
                  {page} / {totalPages}
                </span>
                <button
                  className="px-3 py-1.5 rounded-md text-sm bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] border-none cursor-pointer disabled:opacity-40"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  {t('common.next')}
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {pending && (
        <ConfirmDialog
          title={pending.type === 'role' ? t('admin.users.confirmRoleChange') : t('admin.users.confirmStatusChange')}
          message={pending.type === 'role'
            ? `${pending.user.name || pending.user.email} → ${pending.value}`
            : `${pending.user.name || pending.user.email} → ${pending.value ? t('admin.users.active') : t('admin.users.inactive')}`
          }
          danger={pending.type === 'status' && !pending.value}
          onConfirm={handleConfirm}
          onCancel={() => setPending(null)}
        />
      )}
    </div>
  );
}
