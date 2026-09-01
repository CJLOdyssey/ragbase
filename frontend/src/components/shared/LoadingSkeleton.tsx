interface LoadingSkeletonProps {
  rows?: number;
  type?: 'table' | 'card';
}

export default function LoadingSkeleton({
  rows = 5,
  type = 'table',
}: LoadingSkeletonProps) {
  if (type === 'table') {
    return (
      <div role="status" aria-live="polite" className="flex flex-col gap-1">
        {Array.from({ length: rows }).map((_, i) => (
          <div
            key={i}
            className="flex items-center gap-4 py-3 px-4 border-b border-[var(--color-border)] animate-pulse"
          >
            <div className="h-3 w-3 rounded bg-[var(--color-surface-hover)]" />
            <div
              className="h-3.5 rounded bg-[var(--color-surface-hover)] flex-1"
              style={{ width: `${60 + (i % 4) * 10}%` }}
            />
            <div className="h-3.5 rounded bg-[var(--color-surface-hover)] w-16" />
            <div className="h-3.5 rounded bg-[var(--color-surface-hover)] w-20" />
            <div className="h-3.5 rounded bg-[var(--color-surface-hover)] w-12" />
          </div>
        ))}
      </div>
    );
  }
  return (
    <div role="status" aria-live="polite" className="flex flex-col gap-3 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 p-4 border border-[var(--color-border)] rounded-[var(--radius-card)] animate-pulse"
        >
          <div className="h-4 w-4 rounded bg-[var(--color-surface-hover)]" />
          <div className="flex-1 space-y-2">
            <div className="h-3.5 rounded bg-[var(--color-surface-hover)] w-3/4" />
            <div className="h-3 rounded bg-[var(--color-surface-hover)] w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}
