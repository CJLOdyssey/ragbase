import { File, FileText, Image, X } from 'lucide-react';
import type { AttachedFile } from '../../types/input';

interface Props {
  files: AttachedFile[];
  onRemove: (id: string) => void;
}

function getIcon(name: string) {
  const ext = name.split('.').pop()?.toLowerCase();
  if (/^(png|jpg|jpeg|gif|webp|svg)$/.test(ext || '')) return Image;
  if (/^(txt|md|doc|docx|pdf)$/.test(ext || '')) return FileText;
  return File;
}

function fmtSize(bytes: number) {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

/**
 * Shared attachment list — used by both FileAttach (inside popover) and
 * InputToolbar (inline below the textarea). Single source of truth for
 * rendering attached files.
 */
export default function AttachmentList({ files, onRemove }: Props) {
  if (files.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 px-4">
      {files.map((f) => {
        const Icon = getIcon(f.name);
        return (
          <span
            key={f.id}
            className="inline-flex items-center gap-1.5 px-2 py-1 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-md text-xs"
          >
            <Icon size={14} />
            <span className="max-w-[120px] truncate text-[var(--color-text-primary)]">
              {f.name}
            </span>
            <span className="text-[var(--color-text-muted)] text-xs">
              {fmtSize(f.size)}
            </span>
            <button
              className="p-0.5 bg-transparent border-none rounded text-[var(--color-text-muted)] cursor-pointer flex items-center justify-center hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]"
              onClick={() => onRemove(f.id)}
              type="button"
              aria-label={`Remove ${f.name}`}
            >
              <X size={12} />
            </button>
          </span>
        );
      })}
    </div>
  );
}
