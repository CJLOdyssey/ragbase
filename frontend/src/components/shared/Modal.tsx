import { useEffect, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';

interface Props {
  title: string | ReactNode;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
  hideHeaderBorder?: boolean;
  hideFooterBorder?: boolean;
  bodyClassName?: string;
  ariaLabel?: string;
  width?: number;
}

export default function Modal({
  title,
  onClose,
  children,
  footer,
  className = '',
  hideHeaderBorder,
  hideFooterBorder,
  bodyClassName,
  ariaLabel,
  width,
}: Props) {
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prevFocus = document.activeElement as HTMLElement;
    const modal = contentRef.current;
    if (modal) {
      const firstInput = modal.querySelector<HTMLElement>(
        'input, button, textarea, select, [tabindex]:not([tabindex="-1"])',
      );
      firstInput?.focus();
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      if (e.key !== 'Tab' || !modal) return;
      const focusable = modal.querySelectorAll<HTMLElement>(
        'input, button, textarea, select, [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      prevFocus?.focus();
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 bg-[var(--color-overlay)] flex items-center justify-center z-[var(--z-modal-backdrop)] backdrop-blur-[4px]"
      onClick={onClose}
    >
      <div
        className={`bg-[var(--color-surface-raised)] rounded-xl w-[90%] max-h-[85vh] flex flex-col [box-shadow:var(--shadow-lg)] z-[var(--z-modal)] ${className}`}
        style={width ? { maxWidth: width } : undefined}
        onClick={(e) => e.stopPropagation()}
        ref={contentRef}
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel}
      >
        <div
          className={`flex items-center justify-between px-6 py-4 ${hideHeaderBorder ? '' : 'border-b border-[var(--color-border)]'}`}
        >
          {typeof title === 'string' ? (
            <h3 className="text-lg font-semibold text-[var(--color-text-primary)] m-0">
              {title}
            </h3>
          ) : (
            title
          )}
          <button
            className="bg-transparent border-none text-[var(--color-text-muted)] cursor-pointer p-1 flex items-center justify-center rounded-md transition-[background,color] duration-150 hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
            onClick={onClose}
            aria-label="关闭"
          >
            <X size={18} />
          </button>
        </div>
        <div
          className={`overflow-y-auto flex-1 min-h-0 flex flex-col ${bodyClassName || 'p-5'}`}
        >
          {children}
        </div>
        {footer && (
          <div
            className={`flex items-center justify-end gap-2 px-6 py-4 ${hideFooterBorder ? '' : 'border-t border-[var(--color-border)]'}`}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
