import ConfirmDialog from '../shared/ConfirmDialog';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import type { IndexProgress } from '../../api/client/assets';
import AssetChunksModal from './AssetChunksModal';
import AssetPreviewDrawer from './AssetPreviewDrawer';
import AssetsRenameModal from './AssetsRenameModal';
import AssetsUrlModal from './AssetsUrlModal';
import type { IndexingEntry } from './assetUtils';
import TagEditModal from './TagEditModal';

interface AssetsDialogsProps {
  // tags
  tagTarget: AssetItem | null;
  onTagsClose: () => void;
  onTagsSave: (id: string, tags: string[]) => void;
  tagsSaving: boolean;
  // rename
  renameTarget: AssetItem | null;
  renameValue: string;
  onRenameValueChange: (v: string) => void;
  onRenameClose: () => void;
  onRenameConfirm: () => void;
  // delete
  deleteTarget: AssetItem | null;
  onDeleteConfirm: () => void;
  onDeleteCancel: () => void;
  // url import
  urlOpen: boolean;
  urlValue: string;
  urlName: string;
  onUrlChange: (v: string) => void;
  onUrlNameChange: (v: string) => void;
  onUrlClose: () => void;
  onUrlSubmit: () => void;
  urlSubmitting: boolean;
  // chunks
  chunksTarget: AssetItem | null;
  onChunksClose: () => void;
  // preview
  previewTarget: AssetItem | null;
  indexing: IndexingEntry[];
  progressMap: Record<string, IndexProgress>;
  onPreviewClose: () => void;
  onPreviewChunks: (a: AssetItem) => void;
}

/** 素材页弹窗编排层 — 从页面拆出，保持 AssetsPage 复杂度达标。 */
export default function AssetsDialogs({
  tagTarget,
  onTagsClose,
  onTagsSave,
  tagsSaving,
  renameTarget,
  renameValue,
  onRenameValueChange,
  onRenameClose,
  onRenameConfirm,
  deleteTarget,
  onDeleteConfirm,
  onDeleteCancel,
  urlOpen,
  urlValue,
  urlName,
  onUrlChange,
  onUrlNameChange,
  onUrlClose,
  onUrlSubmit,
  urlSubmitting,
  chunksTarget,
  onChunksClose,
  previewTarget,
  indexing,
  progressMap,
  onPreviewClose,
  onPreviewChunks,
}: AssetsDialogsProps) {
  const { t } = useTranslation();
  return (
    <>
      {tagTarget && (
        <TagEditModal
          key={tagTarget.id}
          asset={tagTarget}
          saving={tagsSaving}
          onClose={onTagsClose}
          onSave={onTagsSave}
        />
      )}

      <AssetsRenameModal
        target={renameTarget}
        value={renameValue}
        onValueChange={onRenameValueChange}
        onClose={onRenameClose}
        onConfirm={onRenameConfirm}
      />

      {deleteTarget && (
        <ConfirmDialog
          title={t('assets.list.rename')}
          message={t('assets.list.deleteConfirm', { name: deleteTarget.name })}
          danger
          onConfirm={onDeleteConfirm}
          onCancel={onDeleteCancel}
        />
      )}

      <AssetsUrlModal
        open={urlOpen}
        urlValue={urlValue}
        urlName={urlName}
        onUrlChange={onUrlChange}
        onNameChange={onUrlNameChange}
        onClose={onUrlClose}
        onSubmit={onUrlSubmit}
        submitting={urlSubmitting}
      />

      {chunksTarget && (
        <AssetChunksModal asset={chunksTarget} onClose={onChunksClose} />
      )}

      {previewTarget && (
        <AssetPreviewDrawer
          asset={previewTarget}
          indexing={indexing}
          progressMap={progressMap}
          onClose={onPreviewClose}
          onOpenChunks={(a) => {
            onPreviewClose();
            onPreviewChunks(a);
          }}
        />
      )}
    </>
  );
}
