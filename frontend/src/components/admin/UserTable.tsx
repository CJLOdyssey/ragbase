import { STATUS_COLORS } from '../shared/statusColors';
import { Avatar, Dropdown, Tag, type MenuProps } from 'antd';
import {
  Eye,
  KeyRound,
  MoreHorizontal,
  Pencil,
  Power,
  Trash2,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AdminUser } from '../../api/client/adminUsers';

export interface UserTableProps {
  users: AdminUser[];
  onEditRole: (user: AdminUser) => void;
  onToggleStatus: (user: AdminUser) => void;
  onResetPassword: (user: AdminUser) => void;
  onView: (user: AdminUser) => void;
  onDelete: (user: AdminUser) => void;
}

type StatusKind = 'active' | 'inactive' | 'inviting';

function getStatusKind(user: AdminUser): StatusKind {
  if (!user.isActive) return 'inactive';
  return 'active';
}

const STATUS_COLOR: Record<StatusKind, string> = {
  active: STATUS_COLORS.green,
  inactive: STATUS_COLORS.gray,
  inviting: STATUS_COLORS.amber,
};

function StatusPill({ kind }: { kind: StatusKind }) {
  const { t } = useTranslation();
  const color = STATUS_COLOR[kind];
  const label =
    kind === 'inactive'
      ? t('admin.users.inactive')
      : kind === 'inviting'
        ? t('admin.users.inviting')
        : t('admin.users.active');
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-medium"
      style={{
        color,
        background: `color-mix(in srgb, ${color} 12%, transparent)`,
        border: `1px solid color-mix(in srgb, ${color} 25%, transparent)`,
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ background: color }}
      />
      {label}
    </span>
  );
}

function RoleBadge({ role }: { role: string }) {
  const isAdmin = role === 'admin';
  const color = isAdmin ? STATUS_COLORS.violet : 'var(--color-accent)';
  return (
    <Tag
      bordered={false}
      style={{
        color,
        background: `color-mix(in srgb, ${color} 12%, transparent)`,
        fontSize: 11,
        marginInlineEnd: 0,
      }}
    >
      {role}
    </Tag>
  );
}

function UserRow({
  user,
  onEditRole,
  onToggleStatus,
  onResetPassword,
  onView,
  onDelete,
}: {
  user: AdminUser;
} & Omit<UserTableProps, 'users'>) {
  const { t } = useTranslation();
  const status = getStatusKind(user);
  const initial = (user.name || user.email || '?')
    .trim()
    .charAt(0)
    .toUpperCase();

  const menuItems: MenuProps['items'] = [
    {
      key: 'edit',
      icon: <Pencil size={13} />,
      label: t('admin.users.role'),
      onClick: () => onEditRole(user),
    },
    {
      key: 'toggle',
      icon: <Power size={13} />,
      label: user.isActive ? t('admin.users.disable') : t('admin.users.enable'),
      onClick: () => onToggleStatus(user),
    },
    {
      key: 'reset',
      icon: <KeyRound size={13} />,
      label: t('admin.users.resetPassword'),
      onClick: () => onResetPassword(user),
    },
    {
      key: 'view',
      icon: <Eye size={13} />,
      label: t('admin.users.viewDetails'),
      onClick: () => onView(user),
    },
    { type: 'divider' },
    {
      key: 'delete',
      icon: <Trash2 size={13} />,
      label: t('admin.users.delete'),
      danger: true,
      onClick: () => onDelete(user),
    },
  ];

  return (
    <div className="grid grid-cols-[2.5fr_90px_80px_130px_80px] items-center px-[18px] h-[62px] border-b border-[color-mix(in_srgb,var(--color-border)_60%,transparent)] hover:bg-[color-mix(in_srgb,var(--color-accent)_5%,transparent)] transition-colors">
      <div className="flex min-w-0 items-center gap-[11px]">
        <Avatar
          size={32}
          style={{
            background: `linear-gradient(135deg,var(--color-accent),${STATUS_COLORS.violet})`,
            color: '#fff',
            fontWeight: 700,
            flexShrink: 0,
          }}
        >
          {initial}
        </Avatar>
        <div className="min-w-0">
          <div className="truncate text-[13.5px] font-medium text-[var(--color-text-primary)]">
            {user.name || user.email}
          </div>
          <div className="truncate text-[11.5px] text-[var(--color-text-muted)] font-mono">
            {user.email}
          </div>
        </div>
      </div>

      <RoleBadge role={user.role} />

      <StatusPill kind={status} />

      <span className="text-[12px] font-mono text-[var(--color-text-muted)]">
        {new Date(user.createdAt).toLocaleDateString()}
      </span>

      <div className="flex justify-end">
        <Dropdown
          menu={{ items: menuItems }}
          trigger={['click']}
          placement="bottomRight"
        >
          <button
            className="flex h-7 w-7 items-center justify-center rounded-md border border-[var(--color-border)] bg-transparent text-[var(--color-text-muted)] cursor-pointer transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
            aria-label={t('admin.users.moreActions')}
          >
            <MoreHorizontal size={15} />
          </button>
        </Dropdown>
      </div>
    </div>
  );
}

export default function UserTable({
  users,
  onEditRole,
  onToggleStatus,
  onResetPassword,
  onView,
  onDelete,
}: UserTableProps) {
  const { t } = useTranslation();
  return (
    <div className="overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)]">
      <div className="grid grid-cols-[2.5fr_90px_80px_130px_80px] items-center px-[18px] h-10 border-b border-[var(--color-border)] bg-[color-mix(in_srgb,var(--color-surface-overlay)_40%,transparent)]">
        {[
          t('admin.users.user'),
          t('admin.users.role'),
          t('admin.users.status'),
          t('admin.users.lastActive'),
          t('admin.users.actions'),
        ].map((h) => (
          <div
            key={h}
            className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--color-text-muted)]"
          >
            {h}
          </div>
        ))}
      </div>
      {users.map((user) => (
        <UserRow
          key={user.userId}
          user={user}
          onEditRole={onEditRole}
          onToggleStatus={onToggleStatus}
          onResetPassword={onResetPassword}
          onView={onView}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
