import { useState } from 'react';
import { File, FileText, Image, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AttachedFile } from '../../types/input';
import { fmtSize, IMAGE_EXT, isImage } from '../../utils/attachmentMeta';

interface Props {
  files: AttachedFile[];
  onRemove: (id: string) => void;
  onPreview?: (file: AttachedFile) => void;
}

function getIcon(name: string) {
  const ext = name.split('.').pop()?.toLowerCase();
  if (IMAGE_EXT.test(ext || '')) return Image;
  if (/^(txt|md|doc|docx|pdf)$/.test(ext || '')) return FileText;
  return File;
}

function renderIcon(name: string) {
  const Icon = getIcon(name);
  return <Icon size={14} />;
}

/**
 * Shared attachment list — used by InputToolbar (attach bar above the textarea).
 * Thumbnails for uploaded images; optional onPreview makes the name a button.
 */
export default function AttachmentList({ files, onRemove, onPreview }: Props) {
  if (files.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 px-4">
      {files.map((f) => (
        <AttachmentChip
          key={f.id}
          file={f}
          onRemove={onRemove}
          onPreview={onPreview}
        />
      ))}
    </div>
  );
}

function AttachmentChip({
  file,
  onRemove,
  onPreview,
}: {
  file: AttachedFile;
  onRemove: (id: string) => void;
  onPreview?: (file: AttachedFile) => void;
}) {
  const [thumbFailed, setThumbFailed] = useState(false);
  const { t } = useTranslation();
  const previewEnabled =
    !!onPreview && file.status === 'done' && !!file.attachmentId;
  const showThumb =
    file.status === 'done' &&
    !!file.attachmentId &&
    isImage(file.name) &&
    !thumbFailed;

  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-1 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-md text-xs">
      {showThumb ? (
        <img
          src={`/api/attachments/${file.attachmentId}`}
          alt={file.name}
          className="h-10 w-10 rounded object-cover"
          onError={() => setThumbFailed(true)}
        />
      ) : (
        renderIcon(file.name)
      )}

      {previewEnabled ? (
        <button
          type="button"
          onClick={() => onPreview?.(file)}
          className="max-w-[240px] inline-flex items-center gap-1.5 bg-transparent border-none p-0 text-left cursor-pointer hover:underline"
          aria-label={`Preview ${file.name}`}
        >
          <span className="max-w-[120px] truncate text-[var(--color-text-primary)]">
            {file.name}
          </span>
          <span className="text-[var(--color-text-muted)] text-xs">
            {fmtSize(file.size)}
          </span>
        </button>
      ) : (
        <span className="inline-flex items-center gap-1.5">
          <span className="max-w-[120px] truncate text-[var(--color-text-primary)]">
            {file.name}
          </span>
          <span className="text-[var(--color-text-muted)] text-xs">
            {fmtSize(file.size)}
          </span>
        </span>
      )}

      {file.status === 'uploading' && (
        <span className="text-[var(--color-text-muted)] text-xs">
          {file.progress ?? 0}%
        </span>
      )}
      {file.status === 'error' && (
        <span className="text-[var(--color-danger)] text-xs">
          {t('attachment.failed')}
        </span>
      )}
      <button
        type="button"
        className="p-0.5 bg-transparent border-none rounded text-[var(--color-text-muted)] cursor-pointer flex items-center justify-center hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]"
        onClick={(e) => {
          e.stopPropagation();
          onRemove(file.id);
        }}
        aria-label={`Remove ${file.name}`}
      >
        <X size={12} />
      </button>
    </span>
  );
}
