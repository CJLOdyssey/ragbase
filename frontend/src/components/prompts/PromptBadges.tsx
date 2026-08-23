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

const STATUS_MAP: Record<string, { colorVar: string; label: string }> = {
  published: { colorVar: '--color-success', label: '启用' },
  active: { colorVar: '--color-success', label: '启用' },
  enabled: { colorVar: '--color-success', label: '启用' },
};

export function StatusBadge({ status }: { status: string }) {
  const entry = STATUS_MAP[status] ?? {
    colorVar: '--color-warning',
    label: '草稿',
  };
  return (
    <SharedStatusPill
      label={entry.label}
      // CSS var() composes fine inside color-mix at the primitive.
      color={`var(${entry.colorVar})`}
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
