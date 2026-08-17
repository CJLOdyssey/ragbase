import {
  File,
  FileCode2,
  FileJson,
  FileSpreadsheet,
  FileText,
  FileType,
  Image,
  type LucideIcon,
} from 'lucide-react';
import type { AttachmentInfo } from '../../types';
import {
  fileIconKey,
  fmtSize,
  isImage,
  typeLabel,
  type IconKey,
} from '../../utils/attachmentMeta';

const ICONS: Record<IconKey, LucideIcon> = {
  image: Image,
  pdf: FileText,
  word: FileText,
  json: FileJson,
  csv: FileSpreadsheet,
  markdown: FileCode2,
  text: FileType,
  generic: File,
};

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
            className="flex items-center gap-3 px-5 py-4 rounded-lg bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] cursor-pointer no-underline transition-colors duration-150 hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
            title={a.filename}
          >
            {(() => {
              const Icon = ICONS[fileIconKey(a)];
              return <Icon size={28} />;
            })()}
            <span className="flex flex-col gap-1 min-w-0">
              <span className="text-[var(--color-text-primary)] truncate max-w-[220px]">
                {a.filename}
              </span>
              <span className="text-[var(--color-text-muted)]">
                {typeLabel(a)}
                {a.size_bytes ? ` · ${fmtSize(a.size_bytes)}` : ''}
              </span>
            </span>
          </a>
        ),
      )}
    </div>
  );
}
