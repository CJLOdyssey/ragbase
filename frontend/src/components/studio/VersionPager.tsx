import { ChevronRight } from 'lucide-react';

interface Props {
  total: number;
  current: number;
  onPrev?: () => void;
  onNext?: () => void;
  prevLabel?: string;
  nextLabel?: string;
}

export default function VersionPager({
  total,
  current,
  onPrev,
  onNext,
  prevLabel = 'Previous user version',
  nextLabel = 'Next user version',
}: Props) {
  if (total < 2) return null;
  return (
    <div className="flex items-center gap-0.5">
      <button
        className="flex items-center justify-center min-w-[32px] min-h-[32px] bg-transparent border border-[var(--color-border)] rounded text-[var(--color-text-muted)] cursor-pointer transition-colors duration-150 p-1 hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-strong)] disabled:opacity-35 disabled:cursor-not-allowed"
        onClick={onPrev}
        disabled={current === 0}
        aria-label={prevLabel}
      >
        <ChevronRight size={12} className="rotate-180" />
      </button>
      <span className="text-xs text-[var(--color-text-muted)] min-w-7 text-center select-none">
        {current + 1}/{total}
      </span>
      <button
        className="flex items-center justify-center min-w-[32px] min-h-[32px] bg-transparent border border-[var(--color-border)] rounded text-[var(--color-text-muted)] cursor-pointer transition-colors duration-150 p-1 hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-strong)] disabled:opacity-35 disabled:cursor-not-allowed"
        onClick={onNext}
        disabled={current === total - 1}
        aria-label={nextLabel}
      >
        <ChevronRight size={12} />
      </button>
    </div>
  );
}
