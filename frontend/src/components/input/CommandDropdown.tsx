import { useCallback, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import type { CommandOption } from '../../types/input';

interface Props {
  commands: CommandOption[];
  activeIndex: number;
  onSelect: (index: number) => void;
  onHover: (index: number) => void;
  onClose: () => void;
}

/**
 * Inline command palette popover — shown when user types '/' in the textarea.
 *
 * Renders filtered commands with keyboard-driven highlight.
 * Positioned above the textarea toolbar.
 */
export default function CommandDropdown({
  commands,
  activeIndex,
  onSelect,
  onHover,
  onClose,
}: Props) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [onClose]);

  // Scroll active item into view
  useEffect(() => {
    if (!listRef.current) return;
    const items = listRef.current.querySelectorAll('[data-cmd-option]');
    items[activeIndex]?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex]);

  const handleClick = useCallback(
    (index: number) => {
      onSelect(index);
    },
    [onSelect],
  );

  if (commands.length === 0) {
    return (
      <div
        className="absolute left-4 right-4 bottom-[calc(100%+6px)] max-h-[280px] overflow-y-auto bg-[var(--color-surface-raised)] rounded-[10px] shadow-[0_12px_40px_rgba(0,0,0,0.25)] z-[500] p-1"
        ref={ref}
      >
        <div className="p-4 text-center text-sm text-[var(--color-text-muted)]">
          {t('model.noCommands')}
        </div>
      </div>
    );
  }

  return (
    <div
      className="absolute left-4 right-4 bottom-[calc(100%+6px)] max-h-[280px] overflow-y-auto bg-[var(--color-surface-raised)] rounded-[10px] shadow-[0_12px_40px_rgba(0,0,0,0.25)] z-[500] p-1"
      ref={ref}
      role="listbox"
    >
      <div ref={listRef}>
        {commands.map((opt, idx) => (
          <button
            key={opt.id}
            data-cmd-option
            className={`flex items-center gap-2 w-full px-3 py-2 border-none rounded-md bg-transparent text-[var(--color-text-primary)] text-sm cursor-pointer transition-colors duration-100 text-left hover:bg-[var(--color-surface-hover)] ${idx === activeIndex ? 'bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)]' : ''}`}
            onClick={() => handleClick(idx)}
            onMouseEnter={() => onHover(idx)}
            role="option"
            aria-selected={idx === activeIndex}
            type="button"
          >
            <span className="font-medium">/{opt.name}</span>
            {opt.source === 'agent' && (
              <span className="inline-block px-1.5 rounded text-[var(--color-accent)] bg-[color-mix(in_srgb,var(--color-accent)_15%,transparent)] text-xs font-bold uppercase tracking-[0.5px] flex-shrink-0 ml-auto">
                Agent
              </span>
            )}
            {opt.description && (
              <span className="text-xs text-[var(--color-text-muted)]">
                {opt.description}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
