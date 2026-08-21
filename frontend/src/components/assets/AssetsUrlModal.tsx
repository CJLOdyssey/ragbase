import Modal from '../shared/Modal';
import { useTranslation } from 'react-i18next';

interface AssetsUrlModalProps {
  open: boolean;
  urlValue: string;
  urlName: string;
  onUrlChange: (v: string) => void;
  onNameChange: (v: string) => void;
  onClose: () => void;
  onSubmit: () => void;
  submitting: boolean;
}

export default function AssetsUrlModal({
  open,
  urlValue,
  urlName,
  onUrlChange,
  onNameChange,
  onClose,
  onSubmit,
  submitting,
}: AssetsUrlModalProps) {
  const { t } = useTranslation();
  if (!open) return null;

  return (
    <Modal
      title={t('assets.urlImport.title')}
      onClose={onClose}
      ariaLabel={t('assets.urlImport.title')}
      width={480}
      hideHeaderBorder
      hideFooterBorder
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
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-accent)] text-white hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
            onClick={onSubmit}
            disabled={!urlValue.trim() || submitting}
          >
            {submitting
              ? t('assets.urlImport.importing')
              : t('assets.urlImport.submit')}
          </button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-[var(--color-text-primary)]">
            {t('assets.urlImport.urlLabel')}
          </label>
          <input
            type="url"
            className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
            placeholder="https://example.com/document.pdf"
            value={urlValue}
            onChange={(e) => onUrlChange(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-[var(--color-text-primary)]">
            {t('assets.urlImport.nameLabel')}
          </label>
          <input
            type="text"
            className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
            placeholder={t('assets.urlImport.namePlaceholder')}
            value={urlName}
            onChange={(e) => onNameChange(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}
