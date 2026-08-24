import { useState } from 'react';
import { Modal as AntdModal, Select } from 'antd';
import { useTranslation } from 'react-i18next';
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
    <AntdModal
      title={`${t('assets.tags.title')} · ${asset.name}`}
      open={true}
      onCancel={onClose}
      centered
      width={460}
      okText={t('confirm.confirm')}
      cancelText={t('confirm.cancel')}
      confirmLoading={saving}
      onOk={() => onSave(asset.id, tags)}
      okButtonProps={{ disabled: tags.length > 20 }}
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
    </AntdModal>
  );
}
