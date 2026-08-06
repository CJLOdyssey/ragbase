import { useTranslation } from 'react-i18next';

interface KeyUsage {
  label: string;
  provider: string;
  usage_type: string;
  is_active: boolean;
  last_used_at: string | null;
  /** 按 Key 拆分消耗 —— 由后端返回，当前预留 */
  today_requests?: number;
  today_tokens?: number;
  month_requests?: number;
  month_tokens?: number;
}

interface Props {
  usage: {
    today_requests: number;
    today_tokens: number;
    month_requests: number;
    month_tokens: number;
  };
  /** 按 Key 拆分消耗 —— 由后端返回，当前预留 */
  keyUsage?: KeyUsage[];
}

export default function ApiUsageTab({ usage, keyUsage }: Props) {
  const { t } = useTranslation();

  return (
    <div className="">
      <div className="flex items-center justify-between mb-4">
        <h4>{t('api.usageStats')}</h4>
      </div>
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-lg p-4 text-center">
          <div className="text-xl font-bold text-[var(--color-text-primary)]">{usage.today_requests}</div>
          <div className="text-xs text-[var(--color-text-muted)] mt-1">{t('api.todayRequests')}</div>
        </div>
        <div className="bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-lg p-4 text-center">
          <div className="text-xl font-bold text-[var(--color-text-primary)]">{usage.today_tokens.toLocaleString()}</div>
          <div className="text-xs text-[var(--color-text-muted)] mt-1">{t('api.todayTokens')}</div>
        </div>
        <div className="bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-lg p-4 text-center">
          <div className="text-xl font-bold text-[var(--color-text-primary)]">{usage.month_requests}</div>
          <div className="text-xs text-[var(--color-text-muted)] mt-1">{t('api.monthRequests')}</div>
        </div>
        <div className="bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-lg p-4 text-center">
          <div className="text-xl font-bold text-[var(--color-text-primary)]">{usage.month_tokens.toLocaleString()}</div>
          <div className="text-xs text-[var(--color-text-muted)] mt-1">{t('api.monthTokens')}</div>
        </div>
      </div>

      {/* === 按 Key 拆分消耗（预留） ===
          当后端返回 keyUsage 数据时，在此展示每个 Key 的独立消耗 */}
      {keyUsage && keyUsage.length > 0 && (
        <div className="border-t border-[var(--color-border)] pt-5">
          <h5 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3 tracking-tight">各 Key 消耗明细</h5>
          <div className="flex flex-col gap-2">
            {keyUsage.map((k) => (
              <div key={k.label} className="flex items-center justify-between py-2.5 px-3.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-lg">
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className={`w-2 h-2 rounded-full shrink-0 ${k.is_active ? 'bg-[var(--color-success)]' : 'bg-[var(--color-text-muted)]'}`} />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-[var(--color-text-primary)] truncate">{k.label || k.provider}</div>
                    <div className="text-xs text-[var(--color-text-muted)]">{k.provider}</div>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-xs text-[var(--color-text-muted)] shrink-0">
                  <span>今日: <strong className="text-[var(--color-text-primary)]">{k.today_requests ?? ''}</strong></span>
                  <span>本月: <strong className="text-[var(--color-text-primary)]">{k.month_requests ?? ''}</strong></span>
                  {k.last_used_at && <span>最后使用: {new Date(k.last_used_at).toLocaleDateString()}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
