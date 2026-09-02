import { useEffect, useState } from 'react';
import FilePreview from '../shared/FilePreview';
import MobileModal from '../shared/MobileModal';
import type { AttachedFile } from '../../types/input';

interface Props {
  file: AttachedFile;
  onClose: () => void;
}

const IMAGE_EXT = /^(png|jpg|jpeg|gif|webp)$/;
const TEXT_EXT = /^(txt|md|json|log|csv|yaml|yml)$/;

function getExt(name: string) {
  return name.split('.').pop()?.toLowerCase() || '';
}

/**
 * Modal preview for an attached file — 复用 FilePreview 共享组件
 * 图片直显 / 文本预加载 / 其他提供下载
 */
export default function AttachmentPreviewModal({ file, onClose }: Props) {
  const ext = getExt(file.name);
  const isImage = IMAGE_EXT.test(ext);
  const isText = TEXT_EXT.test(ext);
  const url = `/api/attachments/${file.attachmentId}`;

  const [fetchState, setFetchState] = useState(() => ({
    url,
    text: null as string | null,
    loading: isText,
    failed: false,
  }));

  const [imgFailed, setImgFailed] = useState(false);

  useEffect(() => {
    if (!isText || !file.attachmentId) return;
    let cancelled = false;
    const controller = new AbortController();
    fetch(url, { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.blob();
      })
      .then((blob) => blob.text())
      .then((content) => {
        if (cancelled) return;
        setFetchState({ url, text: content, loading: false, failed: false });
      })
      .catch((err: unknown) => {
        if (
          cancelled ||
          (err instanceof DOMException && err.name === 'AbortError')
        ) {
          return;
        }
        setFetchState({ url, text: null, loading: false, failed: true });
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [url, isText, file.attachmentId]);

  const current =
    fetchState.url === url
      ? fetchState
      : { url, text: null, loading: isText, failed: false };
  const { text, loading, failed } = current;

  return (
    <MobileModal
      open={true}
      onClose={onClose}
      mode="fullscreen"
      title={file.name}
      footer={null}
    >
      <FilePreview
        url={url}
        fileName={file.name}
        isImage={isImage}
        isText={isText}
        text={text}
        loading={loading}
        failed={failed}
        imgFailed={imgFailed}
        onImgError={() => setImgFailed(true)}
      />
    </MobileModal>
  );
}
