import { useEffect, useState } from 'react';
import FilePreview from '../shared/FilePreview';
import { useQuery } from '@tanstack/react-query';
import { Modal as AntdModal } from 'antd';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import { getAssetContent, type IndexProgress } from '../../api/client/assets';

interface AssetPreviewDrawerProps {
  asset: AssetItem;
  indexing?: { id: string; deadline: number }[];
  progressMap?: Record<string, IndexProgress>;
  onClose: () => void;
  onOpenChunks?: (asset: AssetItem) => void;
}

const IMAGE_EXT = /^(png|jpg|jpeg|gif|webp|bmp|svg)$/;
const TEXT_EXT =
  /^(txt|md|pdf|docx|xlsx|csv|json|log|yaml|yml|doc|xls|html|htm|ppt|pptx)$/;

function getExt(name: string) {
  const idx = name.lastIndexOf('.');
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : '';
}

/**
 * 素材文件预览 — 复用 FilePreview 组件（与 AttachmentPreviewModal 同款交互）
 * 点击列表文件 -> 以文件预览弹窗展示原文件（图片直显 / 文本预加载），不再展示文件信息元数据
 */
export default function AssetPreviewDrawer({
  asset,
  onClose,
}: AssetPreviewDrawerProps) {
  const { t } = useTranslation();
  const ext = getExt(asset.name);
  const isImage = IMAGE_EXT.test(ext);
  const isText = TEXT_EXT.test(ext);
  // 既非图片也非文本（如 zip/二进制）则走 Unsupported 分支，提供下载
  const url = `/api/assets/${asset.id}/file`;
  const [imgFailed, setImgFailed] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset img error when switching preview target
    setImgFailed(false);
  }, [asset.id]);

  const {
    data: contentData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['asset-content', asset.id],
    queryFn: () => getAssetContent(asset.id),
    enabled: isText,
    retry: false,
  });

  const text = contentData?.content ?? null;
  const truncated = contentData?.truncated ?? false;
  const failed = isError;
  const loading = isLoading;

  return (
    <AntdModal
      title={asset.name}
      open={true}
      onCancel={onClose}
      centered
      width={720}
      styles={{
        body: {
          maxHeight: '75vh',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
        },
      }}
      footer={
        <button
          type="button"
          onClick={onClose}
          className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none bg-[var(--color-accent)] text-white hover:opacity-90"
        >
          {t('common.close')}
        </button>
      }
    >
      <FilePreview
        url={url}
        fileName={asset.name}
        isImage={isImage}
        isText={isText}
        text={text}
        loading={loading}
        failed={failed}
        imgFailed={imgFailed}
        truncated={truncated}
        onImgError={() => setImgFailed(true)}
      />
    </AntdModal>
  );
}
