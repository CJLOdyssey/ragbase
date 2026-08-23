/**
 * Shared list badges — single source of truth for list/table/grid visuals.
 *
 * Style baseline: AssetsPage (capsule pills, 27px icon buttons).
 * SRP: each badge renders one visual primitive; domain mapping (which color
 * for which status) stays in the calling feature layer (DIP).
 */
import type { ReactNode } from 'react';

export interface StatusPillProps {
  label: string;
  /** CSS color value (e.g. var(--color-x) or #hex) */
  color: string;
  /** Optional leading dot (admin variant) */
  dot?: boolean;
  testId?: string;
}

export function StatusPill({ label, color, dot, testId }: StatusPillProps) {
  return (
    <span
      data-testid={testId}
      className="inline-flex items-center gap-1.5 justify-center h-7 px-2.5 rounded-full text-[11px] font-medium leading-none whitespace-nowrap"
      style={{
        color,
        background: `color-mix(in_srgb, ${color} 14%, transparent)`,
        border: `1px solid color-mix(in_srgb, ${color} 30%, transparent)`,
      }}
    >
      {dot && (
        <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      )}
      {label}
    </span>
  );
}

export interface MonoBadgeProps {
  children: ReactNode;
}

/** Monospace chip for versions/counts. */
export function MonoBadge({ children }: MonoBadgeProps) {
  return (
    <span className="inline-flex items-center h-5 px-1.5 rounded-md text-[10px] font-mono text-[var(--color-text-secondary)] bg-[var(--color-surface-hover)] border border-[var(--color-border-subtle)] whitespace-nowrap">
      {children}
    </span>
  );
}

export interface TagProps {
  children: ReactNode;
}

/** Small category/tag chip. */
export function Tag({ children }: TagProps) {
  return (
    <span className="inline-flex items-center h-5 px-2 rounded-full text-[10.5px] text-[var(--color-text-secondary)] bg-[color-mix(in_srgb,var(--color-accent)_8%,transparent)] border border-[color-mix(in_srgb,var(--color-accent)_20%,transparent)] whitespace-nowrap">
      {children}
    </span>
  );
}

export interface ActionButtonProps {
  title: string;
  /** CSS variable name consumed for hover tint, e.g. '--color-accent' */
  hoverVar: string;
  onClick: () => void;
  children: ReactNode;
  disabled?: boolean;
  'data-testid'?: string;
}

/** 27px square icon button — stops row click propagation. */
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
