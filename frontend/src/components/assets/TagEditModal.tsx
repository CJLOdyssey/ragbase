import { useState } from 'react';
import { Select } from 'antd';
import { useTranslation } from 'react-i18next';
import MobileModal from '../shared/MobileModal';
import type { AssetItem } from '../../types/assets';

interface TagEditModalProps {
  asset: AssetItem;
  saving: boolean;
  onClose: () => void;
  onSave: (assetId: string, tags: string[]) => void;
}

/** Curated-labels editor — tags ride into chunks at (re)index time and
 * double as a retrieval filter in the recall workbench. */
export default function TagEditModal({
  asset,
  saving,
  onClose,
  onSave,
}: TagEditModalProps) {
  const { t } = useTranslation();
  // Parent remounts this panel per target (key=asset.id) — initial state is
  // the sync point; no setState-in-effect needed.
  const [tags, setTags] = useState<string[]>(asset.tags ?? []);

  return (
    <MobileModal
      open={true}
      onClose={onClose}
      mode="sheet"
      title={`${t('assets.tags.title')} · ${asset.name}`}
      width={460}
      footer={
        <>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
          >
            {t('confirm.cancel')}
          </button>
          <button
            type="button"
            onClick={() => onSave(asset.id, tags)}
            disabled={saving || tags.length > 20}
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-accent)] text-white hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {saving ? '...' : t('confirm.confirm')}
          </button>
        </>
      }
    >
      <div className="flex flex-col gap-2 py-1">
        <Select
          mode="tags"
          value={tags}
          onChange={(v: string[]) =>
            setTags(
              v.map((x) => x.trim().toLowerCase().slice(0, 32)).filter(Boolean),
            )
          }
          placeholder={t('assets.tags.placeholder')}
          maxCount={20}
          className="w-full"
          aria-label={t('assets.tags.title')}
        />
        <p className="text-xs text-[var(--color-text-muted)] m-0">
          {t('assets.tags.hint')}
        </p>
      </div>
    </MobileModal>
  );
}
