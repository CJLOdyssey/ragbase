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

export const ICON_KEYS = {
  image: 'image',
  pdf: 'pdf',
  word: 'word',
  json: 'json',
  csv: 'csv',
  markdown: 'markdown',
  text: 'text',
  generic: 'generic',
} as const;
export type IconKey = (typeof ICON_KEYS)[keyof typeof ICON_KEYS];

const ICON_BY_CONTENT_TYPE: Record<string, IconKey> = {
  'image/png': 'image',
  'image/jpeg': 'image',
  'image/gif': 'image',
  'image/webp': 'image',
  'application/pdf': 'pdf',
  'application/msword': 'word',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
    'word',
  'application/json': 'json',
  'text/csv': 'csv',
  'text/markdown': 'markdown',
  'text/plain': 'text',
};

const ICON_BY_EXT: Record<string, IconKey> = {
  png: 'image',
  jpg: 'image',
  jpeg: 'image',
  gif: 'image',
  webp: 'image',
  pdf: 'pdf',
  doc: 'word',
  docx: 'word',
  json: 'json',
  csv: 'csv',
  md: 'markdown',
  txt: 'text',
};

/** 返回文件类型图标键（数据），UI 层据此映射图标组件 —— 工具层不依赖 UI 库。 */
export function fileIconKey(a: {
  content_type?: string;
  filename: string;
}): IconKey {
  const ct = (a.content_type ?? '').toLowerCase();
  const ext = a.filename.split('.').pop()?.toLowerCase() ?? '';
  return ICON_BY_CONTENT_TYPE[ct] ?? ICON_BY_EXT[ext] ?? 'generic';
}
