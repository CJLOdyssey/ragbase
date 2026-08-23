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
import type { DataTableColumn } from '../shared/list';
import { DataTable } from '../shared/list';
import { StatusPill as SharedStatusPill } from '../shared/list/badges';

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

/** Domain adapter over the shared capsule pill (DIP). */
function StatusPill({ kind }: { kind: StatusKind }) {
  const { t } = useTranslation();
  return (
    <SharedStatusPill
      label={
        kind === 'inactive'
          ? t('admin.users.inactive')
          : kind === 'inviting'
            ? t('admin.users.inviting')
            : t('admin.users.active')
      }
      color={STATUS_COLOR[kind]}
      dot
    />
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

/** Centered cell wrapper matching assets visual baseline. */
function CellCenter({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-center text-center min-w-0">
      {children}
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

  const menuItemsFor = (user: AdminUser): MenuProps['items'] => [
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

  const columns: DataTableColumn[] = [
    { key: 'user', header: t('admin.users.user'), width: '2.5fr' },
    { key: 'role', header: t('admin.users.role'), width: '90px' },
    { key: 'status', header: t('admin.users.status'), width: '80px' },
    { key: 'lastActive', header: t('admin.users.lastActive'), width: '130px' },
    { key: 'actions', header: t('admin.users.actions'), width: '80px' },
  ];

  const renderCell = (
    user: AdminUser,
    col: DataTableColumn,
  ): React.ReactNode => {
    switch (col.key) {
      case 'user': {
        const initial = (user.name || user.email || '?')
          .trim()
          .charAt(0)
          .toUpperCase();
        return (
          <div className="flex min-w-0 items-center gap-[11px] pr-3">
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
        );
      }
      case 'role':
        return (
          <CellCenter>
            <RoleBadge role={user.role} />
          </CellCenter>
        );
      case 'status':
        return (
          <CellCenter>
            <StatusPill kind={getStatusKind(user)} />
          </CellCenter>
        );
      case 'lastActive':
        return (
          <CellCenter>
            <span className="text-[12px] font-mono text-[var(--color-text-muted)]">
              {new Date(user.createdAt).toLocaleDateString()}
            </span>
          </CellCenter>
        );
      case 'actions':
        return (
          <div className="flex justify-center">
            <Dropdown
              menu={{ items: menuItemsFor(user) }}
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
        );
      default:
        return null;
    }
  };

  return (
    <DataTable<AdminUser>
      rows={users}
      columns={columns}
      rowKey={(u) => u.userId}
      renderCell={(row, col) => renderCell(row, col)}
    />
  );
}
