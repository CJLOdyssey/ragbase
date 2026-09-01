/**
 * Prompts-domain badges — thin adapters over shared/list primitives (DIP).
 * Domain mapping (status → label/color) stays here; visuals come from the
 * shared baseline (assets-page capsule look).
 */
import {
  MonoBadge as SharedMonoBadge,
  Tag as SharedTag,
  StatusPill as SharedStatusPill,
} from '../shared/list/badges';
import { useTranslation } from 'react-i18next';

const STATUS_COLORS: Record<string, string> = {
  published: '--color-success',
  active: '--color-success',
  enabled: '--color-success',
};

export function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const colorVar = STATUS_COLORS[status] ?? '--color-warning';
  const isEnabled = !!STATUS_COLORS[status];
  return (
    <SharedStatusPill
      label={isEnabled ? t('prompts.statusEnabled') : t('prompts.statusDraft')}
      // CSS var() composes fine inside color-mix at the primitive.
      color={`var(${colorVar})`}
    />
  );
}

export function MonoBadge({
  children,
}: {
  children: React.ReactNode;
}) {
  return <SharedMonoBadge>{children}</SharedMonoBadge>;
}

export function Tag({ children }: { children: React.ReactNode }) {
  return <SharedTag>{children}</SharedTag>;
}
