import { STATUS_COLORS } from '../shared/statusColors';
import { ShieldCheck, User as UserIcon, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export interface UserStatCardsProps {
  total: number;
  users: { role: string }[];
}

const CARD_BASE =
  'flex items-center gap-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-5 py-4';

const VALUE_BASE = 'text-[22px] font-bold leading-none tracking-[-0.03em]';

function StatIcon({ icon, color }: { icon: React.ReactNode; color: string }) {
  return (
    <div
      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border"
      style={{
        color,
        background: `color-mix(in srgb, ${color} 12%, transparent)`,
        borderColor: `color-mix(in srgb, ${color} 22%, transparent)`,
      }}
    >
      {icon}
    </div>
  );
}

export default function UserStatCards({ total, users }: UserStatCardsProps) {
  const { t } = useTranslation();
  const admins = users.filter((u) => u.role === 'admin').length;
  const members = users.filter((u) => u.role === 'member').length;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <div className={CARD_BASE}>
        <StatIcon icon={<Users size={18} />} color="var(--color-accent)" />
        <div>
          <div className={VALUE_BASE} style={{ color: 'var(--color-accent)' }}>
            {total}
          </div>
          <div className="mt-1 text-[12.5px] text-[var(--color-text-muted)]">
            {t('admin.stats.total')}
          </div>
        </div>
      </div>

      <div className={CARD_BASE}>
        <StatIcon
          icon={<ShieldCheck size={18} />}
          color={STATUS_COLORS.violet}
        />
        <div>
          <div className={VALUE_BASE} style={{ color: STATUS_COLORS.violet }}>
            {admins}
          </div>
          <div className="mt-1 text-[12.5px] text-[var(--color-text-muted)]">
            {t('admin.stats.admins')}
          </div>
        </div>
      </div>

      <div className={CARD_BASE}>
        <StatIcon icon={<UserIcon size={18} />} color={STATUS_COLORS.blue} />
        <div>
          <div className={VALUE_BASE} style={{ color: STATUS_COLORS.blue }}>
            {members}
          </div>
          <div className="mt-1 text-[12.5px] text-[var(--color-text-muted)]">
            {t('admin.stats.members')}
          </div>
        </div>
      </div>
    </div>
  );
}
