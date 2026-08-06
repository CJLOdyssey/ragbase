import React, { createContext, useCallback, useContext, useState } from 'react';
import { AlertCircle, CheckCircle2, X } from 'lucide-react';

interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'info';
}

interface ToastContextValue {
  toast: (message: string, type?: 'success' | 'error' | 'info') => void;
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} });

export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback(
    (message: string, type: 'success' | 'error' | 'info' = 'info') => {
      const id = Date.now();
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 3000);
    },
    [],
  );

  const remove = (id: number) =>
    setToasts((prev) => prev.filter((t) => t.id !== id));

  const iconMap = {
    success: <CheckCircle2 size={16} className="text-green-500" />,
    error: <AlertCircle size={16} className="text-red-500" />,
    info: (
      <CheckCircle2 size={16} className="text-[var(--da-text-secondary)]" />
    ),
  };

  const borderColor = {
    success: 'border-l-[3px] border-l-[var(--da-accent-emerald)]',
    error: 'border-l-[3px] border-l-[var(--danger)]',
    info: 'border-l-[3px] border-l-[var(--da-text-muted)]',
  } as const;

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div
        className="fixed bottom-6 right-6 flex flex-col gap-2 z-[var(--z-toast)] pointer-events-none"
        role="status"
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`flex items-center gap-3 py-3 px-4 bg-[var(--da-bg-elevated)] rounded-lg text-sm text-[var(--da-text-primary)] shadow-lg pointer-events-auto animate-[toast-in_0.2s_ease-out] ${borderColor[t.type]}`}
            role="alert"
          >
            {iconMap[t.type]}
            <span>{t.message}</span>
            <button
              className="bg-transparent border-none text-[var(--da-text-muted)] cursor-pointer p-0.5 ml-auto"
              onClick={() => remove(t.id)}
              aria-label="Close notification"
            >
              <X size={12} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
