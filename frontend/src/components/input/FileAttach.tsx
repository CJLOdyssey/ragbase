import { useCallback, useEffect, useRef } from 'react';
import type * as React from 'react';
import { Paperclip } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { FileRejection } from '../../types/input';

interface Props {
  onAdd: (files: File[]) => void;
  onReject?: (rejections: FileRejection[]) => void;
  /** Number of files currently attached — shown as badge */
  fileCount?: number;
  /** Show remove button next to the badge */
  onRemove?: (id: string) => void;
  /** IDs + names of attached files for the clear-all interaction */
  attachedFiles?: { id: string; name: string }[];
}

// 前端白名单 = 后端 ALLOWED_CONTENT_TYPES 的子集（前端只做即时反馈，后端为准）。
// 不包含 svg：svg 是 active content 载体，OWASP 不建议放行。
const ALLOWED_TYPES = [
  'image/png',
  'image/jpeg',
  'image/gif',
  'image/webp',
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/markdown',
  'application/json',
];

const ALLOWED_EXTENSIONS = ['.doc', '.docx', '.txt', '.md', '.csv'];
const MAX_SIZE = 10 * 1024 * 1024;

function isAllowed(file: File): boolean {
  if (ALLOWED_TYPES.includes(file.type)) return true;
  const name = file.name.toLowerCase();
  return ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

function validateFiles(files: File[]): {
  accepted: File[];
  rejected: FileRejection[];
} {
  const accepted: File[] = [];
  const rejected: FileRejection[] = [];
  for (const f of files) {
    if (f.size > MAX_SIZE) rejected.push({ file: f, reason: 'size_exceeded' });
    else if (!isAllowed(f)) rejected.push({ file: f, reason: 'type_denied' });
    else accepted.push(f);
  }
  return { accepted, rejected };
}

/**
 * File attach button.
 *
 * - Click → native file dialog
 * - Ctrl+V paste on the page → intercepted by useMessageComposer/InputToolbar
 * - Shows a count badge when files are attached
 */
export default function FileAttach({ onAdd, onReject, fileCount = 0 }: Props) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);

  const handleClick = useCallback(() => inputRef.current?.click(), []);

  const handleFiles = useCallback(
    (files: File[]) => {
      if (files.length === 0) return;
      const { accepted, rejected } = validateFiles(files);
      if (accepted.length > 0) onAdd(accepted);
      if (rejected.length > 0) onReject?.(rejected);
    },
    [onAdd, onReject],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files?.length) handleFiles(Array.from(e.target.files));
      e.target.value = '';
    },
    [handleFiles],
  );

  // System-wide paste handler for files (complements textarea-level paste in InputToolbar)
  useEffect(() => {
    const handler = (e: ClipboardEvent) => {
      if (!e.clipboardData?.files.length) return;
      const active = document.activeElement;
      // Only intercept when focus is NOT on another file/text input
      if (active instanceof HTMLInputElement && active.type === 'file') return;
      if (active?.closest('[data-input-wrapper]')) return; // handled by InputToolbar
    };
    document.addEventListener('paste', handler);
    return () => document.removeEventListener('paste', handler);
  }, [handleFiles]);

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        multiple
        onChange={handleChange}
        accept={[...ALLOWED_TYPES, ...ALLOWED_EXTENSIONS].join(',')}
        aria-label={t('fileAttach.attach')}
      />
      <button
        className="p-2 bg-transparent border-none rounded-lg text-[var(--color-text-muted)] cursor-pointer transition-colors duration-150 flex items-center justify-center hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] relative"
        onClick={handleClick}
        title={
          fileCount > 0
            ? t('attachment.countSelected', { count: fileCount })
            : t('fileAttach.attach')
        }
        type="button"
        aria-label={
          fileCount > 0 ? `${fileCount} files attached` : t('fileAttach.attach')
        }
      >
        <Paperclip size={16} />
        {fileCount > 0 && (
          <span className="absolute -top-0.5 -right-1 min-w-[14px] h-[14px] px-1 rounded-[7px] bg-[var(--color-accent)] text-[var(--color-text-on-accent)] text-xs font-bold leading-[14px] text-center pointer-events-none">
            {fileCount}
          </span>
        )}
      </button>
    </>
  );
}
