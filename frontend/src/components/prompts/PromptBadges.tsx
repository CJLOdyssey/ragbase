const STATUS_MAP: Record<string, { colorVar: string; label: string }> = {
  published: { colorVar: '--color-success', label: '已发布' },
  active: { colorVar: '--color-success', label: '已发布' },
  enabled: { colorVar: '--color-success', label: '已发布' },
};

export function StatusBadge({ status }: { status: string }) {
  const entry = STATUS_MAP[status] ?? {
    colorVar: '--color-warning',
    label: '草稿',
  };
  return (
    <span
      className="inline-flex items-center gap-1 px-[7px] py-0.5 rounded-[5px] text-[11px] font-mono whitespace-nowrap border"
      style={{
        background: `color-mix(in srgb, var(${entry.colorVar}) 8%, transparent)`,
        borderColor: `color-mix(in srgb, var(${entry.colorVar}) 18%, transparent)`,
        color: `var(${entry.colorVar})`,
      }}
    >
      <span
        className="w-[5px] h-[5px] rounded-full inline-block shrink-0"
        style={{ background: `var(${entry.colorVar})` }}
      />
      {entry.label}
    </span>
  );
}

export function MonoBadge({
  tone = '--color-success',
  children,
}: {
  tone?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className="px-2 py-0.5 rounded-md text-[11px] font-mono whitespace-nowrap border"
      style={{
        background: `color-mix(in srgb, var(${tone}) 8%, transparent)`,
        borderColor: `color-mix(in srgb, var(${tone}) 18%, transparent)`,
        color: `var(${tone})`,
      }}
    >
      {children}
    </span>
  );
}

export function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="px-[6px] py-px rounded text-[10px] font-mono whitespace-nowrap border"
      style={{
        background: 'color-mix(in srgb, var(--color-accent) 12%, transparent)',
        borderColor: 'color-mix(in srgb, var(--color-accent) 20%, transparent)',
        color: 'var(--color-accent-soft)',
      }}
    >
      {children}
    </span>
  );
}
