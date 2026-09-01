import { useState } from 'react';
import { STATUS_COLORS } from '../shared/statusColors';
import { Avatar, Tag } from 'antd';
import {
  Eye,
  KeyRound,
  MoreHorizontal,
  Pencil,
  Power,
  Trash2,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useIsMobile } from '../../hooks/useMediaQuery';
import ActionSheet, { type ActionSheetItem } from '../shared/ActionSheet';
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
  const isMobile = useIsMobile();
  const [actionUser, setActionUser] = useState<AdminUser | null>(null);

  const actionItems: ActionSheetItem[] = actionUser
    ? [
        {
          key: 'edit',
          icon: <Pencil size={16} />,
          label: t('admin.users.role'),
          onClick: () => onEditRole(actionUser),
        },
        {
          key: 'toggle',
          icon: <Power size={16} />,
          label: actionUser.isActive
            ? t('admin.users.disable')
            : t('admin.users.enable'),
          onClick: () => onToggleStatus(actionUser),
        },
        {
          key: 'reset',
          icon: <KeyRound size={16} />,
          label: t('admin.users.resetPassword'),
          onClick: () => onResetPassword(actionUser),
        },
        {
          key: 'view',
          icon: <Eye size={16} />,
          label: t('admin.users.viewDetails'),
          onClick: () => onView(actionUser),
        },
        {
          key: 'delete',
          icon: <Trash2 size={16} />,
          label: t('admin.users.delete'),
          danger: true,
          onClick: () => onDelete(actionUser),
        },
      ]
    : [];

  const columns: DataTableColumn[] = [
    { key: 'user', header: t('admin.users.user'), width: '2.5fr' },
    { key: 'role', header: t('admin.users.role'), width: '90px' },
    { key: 'status', header: t('admin.users.status'), width: '80px' },
    // 后端仅返回 created_at（无 last_active 字段）——列名与数据语义对齐，
    // 避免「最近活跃」显示注册时间造成误导。
    { key: 'lastActive', header: t('admin.users.createdAt'), width: '130px' },
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
            {isMobile ? (
              <>
                <button
                  className="flex h-7 w-7 items-center justify-center rounded-md border border-[var(--color-border)] bg-transparent text-[var(--color-text-muted)] cursor-pointer transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
                  aria-label={t('admin.users.moreActions')}
                  onClick={() => setActionUser(user)}
                >
                  <MoreHorizontal size={15} />
                </button>
                <ActionSheet
                  open={actionUser?.userId === user.userId}
                  onClose={() => setActionUser(null)}
                  items={actionItems}
                />
              </>
            ) : (
              <button
                className="flex h-7 w-7 items-center justify-center rounded-md border border-[var(--color-border)] bg-transparent text-[var(--color-text-muted)] cursor-pointer transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
                aria-label={t('admin.users.moreActions')}
                onClick={() => setActionUser(user)}
              >
                <MoreHorizontal size={15} />
              </button>
            )}
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
