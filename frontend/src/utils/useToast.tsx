import React, {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from 'react';
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
  // 自增 id：同一毫秒内连续两条 toast 不碰撞（Date.now() 会 key 冲突，
  // 且第一个 3s 定时器会把两条一起移除）。
  const nextIdRef = useRef(1);

  const toast = useCallback(
    (message: string, type: 'success' | 'error' | 'info' = 'info') => {
      const id = nextIdRef.current++;
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
      <CheckCircle2 size={16} className="text-[var(--color-text-secondary)]" />
    ),
  };

  const borderColor = {
    success: 'border-l-[3px] border-l-[var(--color-success)]',
    error: 'border-l-[3px] border-l-[var(--color-danger)]',
    info: 'border-l-[3px] border-l-[var(--color-text-muted)]',
  } as const;

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {/* 移动端：底部居中全宽胶囊（safe-area 之上），拇指可及；
          桌面端：右下角堆叠（原行为）。 */}
      <div
        className="fixed z-[var(--z-toast)] pointer-events-none flex flex-col gap-2 inset-x-0 bottom-0 px-4 pb-[max(env(safe-area-inset-bottom),16px)] items-center md:inset-x-auto md:right-6 md:bottom-6 md:px-0 md:pb-0 md:items-end"
        role="status"
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`flex items-center gap-3 py-3 px-4 bg-[var(--color-surface-elevated)] rounded-lg text-sm text-[var(--color-text-primary)] shadow-lg pointer-events-auto animate-[toast-in_0.2s_ease-out] w-full max-w-[480px] md:w-auto ${borderColor[t.type]}`}
            role="alert"
          >
            {iconMap[t.type]}
            <span className="min-w-0">{t.message}</span>
            <button
              className="bg-transparent border-none text-[var(--color-text-muted)] cursor-pointer p-0.5 ml-auto shrink-0"
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
