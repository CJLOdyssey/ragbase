import Modal from '../shared/Modal';
import { useTranslation } from 'react-i18next';
import type { VersionItem } from '../../api/client/versions';

interface Props {
  version: VersionItem;
  onRollback: () => void;
  onClose: () => void;
}

export default function VersionViewModal({
  version,
  onRollback,
  onClose,
}: Props) {
  const { t } = useTranslation();
  const snap = version.snapshot as Record<string, string>;
  const snapName = snap.name ?? '—';
  const snapCategory = snap.category ?? '—';
  const snapContent = snap.content ?? '';

  return (
    <Modal
      title={t('prompts.version.rollbackTitle', {
        version: `v${version.version_num}`,
      })}
      onClose={onClose}
      ariaLabel={t('prompts.version.rollbackTitle', {
        version: `v${version.version_num}`,
      })}
      width={560}
      footer={
        <>
          <button
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
            onClick={onClose}
          >
            {t('common.close')}
          </button>
          <button
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-accent)] text-white hover:opacity-90"
            onClick={onRollback}
          >
            {t('prompts.version.rollbackConfirm')}
          </button>
        </>
      }
    >
      <div className="flex flex-col gap-4 p-6">
        {/* Metadata */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <span className="block text-xs text-[var(--color-text-muted)] mb-1">
              {t('prompts.editor.name')}
            </span>
            <span className="text-sm text-[var(--color-text-primary)]">
              {snapName}
            </span>
          </div>
          <div>
            <span className="block text-xs text-[var(--color-text-muted)] mb-1">
              {t('prompts.editor.category')}
            </span>
            <span className="text-sm text-[var(--color-text-primary)]">
              {snapCategory}
            </span>
          </div>
        </div>

        {/* Content */}
        <div>
          <span className="block text-xs text-[var(--color-text-muted)] mb-1">
            {t('prompts.editor.content')}
          </span>
          <pre className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] overflow-x-auto whitespace-pre-wrap font-mono m-0 min-h-[120px]">
            {snapContent}
          </pre>
        </div>
      </div>
    </Modal>
  );
}
