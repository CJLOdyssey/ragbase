import { Paperclip } from 'lucide-react';
import type { AttachmentInfo } from '../../types';
import { fmtSize, isImage, typeLabel } from '../../utils/attachmentMeta';

interface Props {
  attachments: AttachmentInfo[];
}

export default function MessageAttachments({ attachments }: Props) {
  if (attachments.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5 justify-end mt-1">
      {attachments.map((a) =>
        isImage(a.filename) || (a.content_type ?? '').startsWith('image/') ? (
          <a
            key={a.id}
            href={`/api/attachments/${a.id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 cursor-pointer"
            title={a.filename}
          >
            <img
              src={`/api/attachments/${a.id}`}
              alt={a.filename}
              className="h-20 w-20 object-cover rounded-lg border border-[var(--color-border)]"
            />
          </a>
        ) : (
          <a
            key={a.id}
            href={`/api/attachments/${a.id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] text-xs cursor-pointer no-underline transition-colors duration-150 hover:text-[var(--color-text-primary)]"
            title={a.filename}
          >
            <Paperclip size={12} />
            <span className="max-w-[160px] truncate">{a.filename}</span>
            {typeLabel(a) && (
              <span className="shrink-0 px-1 py-0.5 rounded bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)] text-[var(--color-accent)] font-medium">
                {typeLabel(a)}
              </span>
            )}
            {a.size_bytes ? (
              <span className="shrink-0 text-[var(--color-text-muted)]">
                {fmtSize(a.size_bytes)}
              </span>
            ) : null}
          </a>
        ),
      )}
    </div>
  );
}
