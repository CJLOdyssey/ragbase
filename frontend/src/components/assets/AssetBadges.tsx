import type { ReactNode } from 'react';
import { STATUS_COLORS } from '../shared/statusColors';
import { useTranslation } from 'react-i18next';
import { extColorOf, type AssetStatus } from './assetUtils';

const STATUS_COLOR: Record<AssetStatus, string> = {
  indexed: STATUS_COLORS.green,
  processing: STATUS_COLORS.amber,
  failed: STATUS_COLORS.red,
  pending: STATUS_COLORS.gray,
};

export function StatusPill({ status }: { status: AssetStatus }) {
  const { t } = useTranslation();
  const color = STATUS_COLOR[status];
  const label = t(`assets.status.${status}`);
  return (
    <span
      data-testid={`status-${status}`}
      className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium leading-none whitespace-nowrap"
      style={{
        color,
        background: `color-mix(in_srgb, ${color} 14%, transparent)`,
        border: `1px solid color-mix(in_srgb, ${color} 30%, transparent)`,
      }}
    >
      {label}
    </span>
  );
}

export function ExtBadge({ ext }: { ext: string }) {
  const color = extColorOf(ext);
  return (
    <span
      className="inline-flex items-center justify-center h-7 w-7 rounded-[7px] text-[9px] font-bold uppercase font-mono shrink-0"
      style={{
        color,
        background: `color-mix(in_srgb, ${color} 12%, transparent)`,
        border: `1px solid color-mix(in_srgb, ${color} 24%, transparent)`,
      }}
    >
      {ext || '?'}
    </span>
  );
}

interface ActionButtonProps {
  title: string;
  hoverVar: string;
  onClick: () => void;
  children: ReactNode;
  disabled?: boolean;
  'data-testid'?: string;
}

export function ActionButton({
  title,
  hoverVar,
  onClick,
  children,
  disabled,
  'data-testid': testId,
}: ActionButtonProps) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      disabled={disabled}
      data-testid={testId}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className="w-[27px] h-[27px] rounded-md border bg-[var(--color-surface)] text-[var(--color-text-muted)] cursor-pointer inline-flex items-center justify-center transition-colors border-[var(--color-border)] hover:bg-[color-mix(in_srgb,var(--hover)_12%,transparent)] hover:text-[var(--hover)] hover:border-[color-mix(in_srgb,var(--hover)_30%,transparent)] disabled:opacity-50 disabled:cursor-not-allowed"
      style={{ ['--hover' as string]: `var(${hoverVar})` }}
    >
      {children}
    </button>
  );
}
