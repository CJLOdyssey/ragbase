import type { ReactNode } from 'react';
import { AlertTriangle, OctagonX } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import Modal from './Modal';

interface ConfirmDialogProps {
  title: string | ReactNode;
  message: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  icon?: ReactNode;
  onConfirm: () => void;
  onCancel: () => void;
  width?: number;
}

export default function ConfirmDialog({
  title,
  message,
  confirmLabel: confirmLabelProp,
  cancelLabel: cancelLabelProp,
  danger,
  icon,
  onConfirm,
  onCancel,
  width,
}: ConfirmDialogProps) {
  const { t } = useTranslation();
  const confirmLabel = confirmLabelProp ?? t('confirm.confirm');
  const cancelLabel = cancelLabelProp ?? t('confirm.cancel');
  const Icon =
    icon ??
    (danger ? (
      <OctagonX
        size={24}
        className="text-[var(--color-danger)]"
        aria-label={t('confirm.danger')}
      />
    ) : (
      <AlertTriangle
        size={24}
        className="text-[var(--color-accent-soft)]"
        aria-label={t('confirm.info')}
      />
    ));

  return (
    <Modal
      title={title}
      onClose={onCancel}
      hideHeaderBorder
      hideFooterBorder
      ariaLabel={typeof title === 'string' ? title : undefined}
      width={width}
      className="w-[var(--modal-sm)]"
      footer={
        <>
          <button
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
            onClick={onCancel}
          >
            {cancelLabel}
          </button>
          <button
            className={`inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 ${
              danger
                ? 'bg-[color-mix(in_srgb,var(--color-danger)_15%,transparent)] text-[var(--color-danger)] hover:bg-[color-mix(in_srgb,var(--color-danger)_25%,transparent)]'
                : 'bg-[var(--color-surface-hover)] text-[var(--color-text-primary)] hover:bg-[var(--color-surface-elevated)]'
            }`}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </>
      }
    >
      <div className="flex items-start gap-4 p-6">
        {Icon}
        <div>
          <p style={{ fontWeight: 600, marginBottom: 4 }}>
            {danger ? t('confirm.danger') : t('confirm.info')}
          </p>
          <p>{message}</p>
        </div>
      </div>
    </Modal>
  );
}
