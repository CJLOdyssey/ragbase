import { STATUS_COLORS } from '../shared/statusColors';
import type { AssetItem } from '../../types/assets';
import type { IndexProgress } from '../../api/client/assets';

export interface IndexingEntry {
  id: string;
  deadline: number;
}

export type AssetStatus =
  'indexed' | 'processing' | 'failed' | 'pending' | 'noIndex';

export const STATUS_OPTIONS: readonly AssetStatus[] = [
  'indexed',
  'processing',
  'failed',
  'pending',
  'noIndex',
] as const;

export const FORMAT_OPTIONS = [
  'pdf',
  'txt',
  'md',
  'docx',
  'xlsx',
  'csv',
  'png',
  'jpg',
  'jpeg',
  'webp',
  'gif',
  'doc',
  'xls',
  'ppt',
  'pptx',
  'html',
  'htm',
] as const;
export type FormatOption = (typeof FORMAT_OPTIONS)[number];

export const FORMAT_REGISTRY: Record<
  string,
  { label: string; category: 'document' | 'image' | 'data' }
> = {
  pdf: { label: 'PDF', category: 'document' },
  txt: { label: 'TXT', category: 'document' },
  md: { label: 'MD', category: 'document' },
  doc: { label: 'DOC', category: 'document' },
  docx: { label: 'DOCX', category: 'document' },
  xlsx: { label: 'XLSX', category: 'data' },
  xls: { label: 'XLS', category: 'data' },
  csv: { label: 'CSV', category: 'data' },
  html: { label: 'HTML', category: 'document' },
  htm: { label: 'HTM', category: 'document' },
  ppt: { label: 'PPT', category: 'document' },
  pptx: { label: 'PPTX', category: 'document' },
  png: { label: 'PNG', category: 'image' },
  jpg: { label: 'JPG', category: 'image' },
  jpeg: { label: 'JPEG', category: 'image' },
  webp: { label: 'WEBP', category: 'image' },
  gif: { label: 'GIF', category: 'image' },
  bmp: { label: 'BMP', category: 'image' },
};

export type TimeRange = 'all' | 'today' | '7d' | '30d' | 'custom';
export const TIME_RANGES: {
  value: TimeRange;
  labelKey: string;
  defaultLabel: string;
}[] = [
  { value: 'all', labelKey: 'assets.filter.timeAll', defaultLabel: '全部' },
  { value: 'today', labelKey: 'assets.filter.timeToday', defaultLabel: '今天' },
  { value: '7d', labelKey: 'assets.filter.time7d', defaultLabel: '最近7天' },
  { value: '30d', labelKey: 'assets.filter.time30d', defaultLabel: '最近30天' },
  {
    value: 'custom',
    labelKey: 'assets.filter.timeCustom',
    defaultLabel: '自定义范围',
  },
];

export function resolveTimeRange(
  range: TimeRange,
  customFrom: string,
  customTo: string,
): { from: number | null; to: number | null } {
  const now = new Date();
  const endOfToday = new Date(now);
  endOfToday.setHours(23, 59, 59, 999);
  const startOfToday = new Date(now);
  startOfToday.setHours(0, 0, 0, 0);
  if (range === 'all') return { from: null, to: null };
  if (range === 'today')
    return { from: startOfToday.getTime(), to: endOfToday.getTime() };
  if (range === '7d') {
    const from = new Date(startOfToday);
    from.setDate(from.getDate() - 6);
    return { from: from.getTime(), to: endOfToday.getTime() };
  }
  if (range === '30d') {
    const from = new Date(startOfToday);
    from.setDate(from.getDate() - 29);
    return { from: from.getTime(), to: endOfToday.getTime() };
  }
  if (range === 'custom') {
    const from = customFrom ? new Date(customFrom).getTime() : null;
    const to = customTo
      ? new Date(new Date(customTo).setHours(23, 59, 59, 999)).getTime()
      : null;
    return { from, to };
  }
  return { from: null, to: null };
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function getExt(name: string): string {
  const idx = name.lastIndexOf('.');
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : '';
}

const ACCENT = 'var(--color-accent)';

const EXT_COLORS: Record<string, string> = {
  txt: STATUS_COLORS.blue,
  md: STATUS_COLORS.green,
  pdf: STATUS_COLORS.red,
  doc: ACCENT,
  docx: ACCENT,
  xls: STATUS_COLORS.green,
  xlsx: STATUS_COLORS.green,
  csv: STATUS_COLORS.amber,
  html: STATUS_COLORS.blue,
  htm: STATUS_COLORS.blue,
  ppt: STATUS_COLORS.amber,
  pptx: STATUS_COLORS.amber,
  png: STATUS_COLORS.violet,
  jpg: STATUS_COLORS.violet,
  jpeg: STATUS_COLORS.violet,
  webp: STATUS_COLORS.violet,
  gif: STATUS_COLORS.violet,
  bmp: STATUS_COLORS.violet,
};

export function extColorOf(ext: string): string {
  return EXT_COLORS[ext] ?? ACCENT;
}

export function isLiveIndexing(
  asset: AssetItem,
  indexing: IndexingEntry[],
): boolean {
  const now = Date.now();
  return indexing.some((i) => i.id === asset.id && i.deadline > now);
}

export function getAssetStatus(
  asset: AssetItem,
  indexing: IndexingEntry[],
  progress?: IndexProgress | null,
): AssetStatus {
  if (asset.assetType === 'image') return 'noIndex';
  if (asset.indexed) return 'indexed';
  if (isLiveIndexing(asset, indexing)) {
    return progress?.stage === 'failed' ? 'failed' : 'processing';
  }
  if (progress) return 'failed';
  return 'pending';
}

export interface AssetStats {
  total: number;
  indexed: number;
  processing: number;
  failed: number;
  pending: number;
  totalBytes: number;
}

export function computeStats(
  assets: AssetItem[],
  indexing: IndexingEntry[],
  progressMap: Record<string, IndexProgress> = {},
): AssetStats {
  let indexed = 0;
  let processing = 0;
  let failed = 0;
  let pending = 0;
  let totalBytes = 0;
  for (const a of assets) {
    totalBytes += a.sizeBytes;
    // 图片无需索引，不占用 pending/failed 计数，保持状态与操作对齐
    if (a.assetType === 'image') continue;
    if (a.indexed) {
      indexed += 1;
      continue;
    }
    if (isLiveIndexing(a, indexing)) {
      const p = progressMap[a.id];
      if (p?.stage === 'failed') failed += 1;
      else processing += 1;
      continue;
    }
    if (progressMap[a.id]) {
      failed += 1;
      continue;
    }
    pending += 1;
  }
  return {
    total: assets.length,
    indexed,
    processing,
    failed,
    pending,
    totalBytes,
  };
}
