export const IMAGE_EXT = /^(png|jpg|jpeg|gif|webp)$/;

export function isImage(filename: string): boolean {
  return IMAGE_EXT.test(filename.split('.').pop()?.toLowerCase() || '');
}

export function fmtSize(bytes?: number): string {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

const TYPE_LABELS: Record<string, string> = {
  'application/pdf': 'PDF',
  'text/plain': 'TXT',
  'text/markdown': 'MD',
  'text/csv': 'CSV',
  'application/json': 'JSON',
  'application/msword': 'DOC',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
    'DOCX',
};

export function typeLabel(a: {
  content_type?: string;
  filename: string;
}): string {
  if (a.content_type && TYPE_LABELS[a.content_type])
    return TYPE_LABELS[a.content_type];
  const ext = a.filename.split('.').pop()?.toUpperCase();
  return ext || a.content_type || '';
}
