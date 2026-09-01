import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import MobileModal from './MobileModal';

/** ActionSheetItem — 选项描述；移动端渲染为底部 Sheet 选项列表，桌面端为居中弹窗列表 */
export interface ActionSheetItem {
  key: string;
  label: ReactNode;
  icon?: ReactNode;
  danger?: boolean;
  disabled?: boolean;
  onClick: () => void;
}

interface ActionSheetProps {
  open: boolean;
  onClose: () => void;
  items: ActionSheetItem[];
  title?: ReactNode;
  cancelLabel?: string;
}

/** ActionSheet — 选项菜单（移动端底部 Sheet + 独立取消块，iOS 惯例）。
 *  通过 MobileModal 的 sheet 模式获得贴底/圆角/拖拽关闭/安全区行为。 */
export default function ActionSheet({
  open,
  onClose,
  items,
  title,
  cancelLabel,
}: ActionSheetProps) {
  const { t } = useTranslation();

  return (
    <MobileModal open={open} onClose={onClose} mode="sheet" footer={null}>
      {title && (
        <div className="px-5 pt-2 pb-1 text-sm text-[var(--color-text-muted)] text-center">
          {title}
        </div>
      )}
      <div className="flex flex-col px-2 py-2">
        {items.map((item) => (
          <button
            key={item.key}
            type="button"
            disabled={item.disabled}
            onClick={() => {
              item.onClick();
              onClose();
            }}
            className={`flex items-center gap-3 w-full h-12 px-4 border-none bg-transparent rounded-lg text-sm cursor-pointer transition-colors duration-100 active:bg-[var(--color-surface-hover)] disabled:cursor-not-allowed disabled:opacity-40 ${
              item.danger
                ? 'text-[var(--color-danger)]'
                : 'text-[var(--color-text-primary)]'
            }`}
          >
            {item.icon && <span className="shrink-0">{item.icon}</span>}
            <span className="flex-1 text-left truncate">{item.label}</span>
          </button>
        ))}
      </div>
      <div className="h-px bg-[var(--color-border-subtle)] mx-2" aria-hidden="true" />
      <div className="px-2 py-2">
        <button
          type="button"
          onClick={onClose}
          className="flex items-center justify-center w-full h-12 border-none bg-transparent rounded-lg text-sm font-medium text-[var(--color-text-secondary)] cursor-pointer transition-colors duration-100 active:bg-[var(--color-surface-hover)]"
        >
          {cancelLabel ?? t('common.cancel')}
        </button>
      </div>
    </MobileModal>
  );
}