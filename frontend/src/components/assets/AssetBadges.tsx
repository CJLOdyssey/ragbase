/**
 * Assets-domain badges — thin adapters over shared/list primitives (DIP).
 *
 * Domain mapping (status → color/label/testid) stays here; the visual
 * primitive lives in shared/list/badges so every list page shares one look.
 */
import {
  ActionButton as SharedActionButton,
  StatusPill as SharedStatusPill,
  type ActionButtonProps,
} from '../shared/list/badges';
import { STATUS_COLORS } from '../shared/statusColors';
import { useTranslation } from 'react-i18next';
import { extColorOf, type AssetStatus } from './assetUtils';

const STATUS_COLOR: Record<AssetStatus, string> = {
  indexed: STATUS_COLORS.green,
  processing: STATUS_COLORS.amber,
  failed: STATUS_COLORS.red,
  pending: STATUS_COLORS.gray,
  noIndex: STATUS_COLORS.violet,
};

export function StatusPill({
  status,
  title,
}: {
  status: AssetStatus;
  /** 失败原因 tooltip（仅 failed 态由调用方传入） */
  title?: string;
}) {
  const { t } = useTranslation();
  return (
    <SharedStatusPill
      label={t(`assets.status.${status}`)}
      color={STATUS_COLOR[status]}
      testId={`status-${status}`}
      title={title}
    />
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

/** Re-export under the same contract consumers already use. */
export function ActionButton(props: ActionButtonProps) {
  return <SharedActionButton {...props} />;
}
