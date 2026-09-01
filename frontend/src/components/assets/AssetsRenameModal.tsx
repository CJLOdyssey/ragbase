import { useTranslation } from 'react-i18next';
import MobileModal from '../shared/MobileModal';
import type { AssetItem } from '../../types/assets';

interface AssetsRenameModalProps {
  target: AssetItem | null;
  value: string;
  onValueChange: (v: string) => void;
  onClose: () => void;
  onConfirm: () => void;
}

function splitName(name: string): { base: string; ext: string } {
  const idx = name.lastIndexOf('.');
  if (idx > 0 && idx < name.length - 1) {
    return { base: name.slice(0, idx), ext: name.slice(idx) };
  }
  return { base: name, ext: '' };
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
  const { ext } = splitName(target.name);

  return (
    <MobileModal
      open={true}
      onClose={onClose}
      mode="sheet"
      title={t('assets.list.rename')}
      width={420}
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
      <div className="flex items-center gap-2">
        <input
          type="text"
          className="flex-1 min-w-0 px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
          value={value}
          onChange={(e) => onValueChange(e.target.value)}
          data-testid="rename-input"
          aria-label={t('assets.list.rename')}
          placeholder={splitName(target.name).base}
        />
        {ext && (
          <span
            className="shrink-0 text-sm font-mono text-[var(--color-text-muted)] select-none"
            aria-hidden
          >
            {ext}
          </span>
        )}
      </div>
    </MobileModal>
  );
}
