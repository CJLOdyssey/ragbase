import Modal from '../shared/Modal';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';

interface AssetsRenameModalProps {
  target: AssetItem | null;
  value: string;
  onValueChange: (v: string) => void;
  onClose: () => void;
  onConfirm: () => void;
}

export default function AssetsRenameModal({
  target,
  value,
  onValueChange,
  onClose,
  onConfirm,
}: AssetsRenameModalProps) {
  const { t } = useTranslation();
  if (!target) return null;

  return (
    <Modal
      title={t('assets.list.rename')}
      onClose={onClose}
      ariaLabel={t('assets.list.rename')}
      width={420}
      hideHeaderBorder
      bodyClassName="p-6"
      footer={
        <>
          <button
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]"
            onClick={onClose}
          >
            {t('confirm.cancel')}
          </button>
          <button
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-accent)] text-white hover:opacity-90"
            onClick={onConfirm}
          >
            {t('confirm.confirm')}
          </button>
        </>
      }
    >
      <input
        type="text"
        className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
        value={value}
        onChange={(e) => onValueChange(e.target.value)}
        data-testid="rename-input"
        aria-label={t('assets.list.rename')}
      />
    </Modal>
  );
}
