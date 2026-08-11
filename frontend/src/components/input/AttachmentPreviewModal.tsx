import { useEffect, useRef, useState } from 'react';
import { Download, Loader2, X } from 'lucide-react';
import type { AttachedFile } from '../../types/input';

interface Props {
  file: AttachedFile;
  onClose: () => void;
}

const IMAGE_EXT = /^(png|jpg|jpeg|gif|webp)$/;
const TEXT_EXT = /^(txt|md|json|log|csv|yaml|yml)$/;
const PREVIEW_CHAR_LIMIT = 64 * 1024;

function getExt(name: string) {
  return name.split('.').pop()?.toLowerCase() || '';
}

/**
 * Modal preview for an attached file: image renders large, text is fetched
 * and shown (truncated), other types get a download link.
 */
export default function AttachmentPreviewModal({ file, onClose }: Props) {
  const ext = getExt(file.name);
  const isImage = IMAGE_EXT.test(ext);
  const isText = TEXT_EXT.test(ext);
  const url = `/api/attachments/${file.attachmentId}`;

  const dialogRef = useRef<HTMLDivElement>(null);

  const [fetchState, setFetchState] = useState(() => ({
    url,
    text: null as string | null,
    loading: isText,
    failed: false,
  }));

  const [imgFailed, setImgFailed] = useState(false);

  useEffect(() => {
    const prevFocused = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();
    return () => prevFocused?.focus();
  }, []);

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

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  const truncated =
    text !== null && text.length > PREVIEW_CHAR_LIMIT
      ? `${text.slice(0, PREVIEW_CHAR_LIMIT)}\n\n…(内容过长，已截断)`
      : text;

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-label={`Preview ${file.name}`}
      tabIndex={-1}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-6 outline-none"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="max-w-3xl w-full max-h-[80vh] flex flex-col rounded-2xl bg-[var(--color-surface-raised)] border border-[var(--color-border)] shadow-2xl overflow-hidden">
        <header className="flex items-center justify-between gap-4 px-5 py-3 border-b border-[var(--color-border)]">
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)] truncate">
            {file.name}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close preview"
            className="p-1.5 bg-transparent border-none rounded-lg text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
          >
            <X size={16} />
          </button>
        </header>

        <div className="flex-1 overflow-auto p-5">
          {isImage &&
            (imgFailed ? (
              <div className="py-8 text-center">
                <p className="text-sm text-[var(--color-danger)] mb-4">
                  图片加载失败
                </p>
                <a
                  href={url}
                  download
                  className="inline-flex items-center gap-1.5 text-sm text-[var(--color-accent)] hover:underline"
                >
                  <Download size={14} />
                  下载文件
                </a>
              </div>
            ) : (
              <img
                src={url}
                alt={file.name}
                className="mx-auto max-w-full max-h-[70vh] object-contain rounded-lg"
                onError={() => setImgFailed(true)}
              />
            ))}

          {isText && loading && (
            <div className="flex items-center justify-center gap-2 py-10 text-[var(--color-text-muted)] text-sm">
              <Loader2 size={18} className="animate-spin" />
              加载中…
            </div>
          )}

          {isText && failed && (
            <div className="py-8 text-center">
              <p className="text-sm text-[var(--color-danger)] mb-4">
                预览加载失败
              </p>
              <a
                href={url}
                download
                className="inline-flex items-center gap-1.5 text-sm text-[var(--color-accent)] hover:underline"
              >
                <Download size={14} />
                下载文件
              </a>
            </div>
          )}

          {isText && text !== null && (
            <pre className="whitespace-pre-wrap break-words text-sm leading-relaxed text-[var(--color-text-primary)]">
              {truncated}
            </pre>
          )}

          {!isImage && !isText && (
            <div className="py-8 text-center">
              <p className="text-sm text-[var(--color-text-muted)] mb-4">
                暂不支持预览该类型
              </p>
              <a
                href={url}
                download
                className="inline-flex items-center gap-1.5 text-sm text-[var(--color-accent)] hover:underline"
              >
                <Download size={14} />
                下载文件
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
