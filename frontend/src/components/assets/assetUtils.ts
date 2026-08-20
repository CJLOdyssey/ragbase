import { STATUS_COLORS } from '../shared/statusColors';
import type { AssetItem } from '../../types/assets';
import type { IndexProgress } from '../../api/client/assets';

export interface IndexingEntry {
  id: string;
  deadline: number;
}

export type AssetStatus = 'indexed' | 'processing' | 'failed' | 'pending';

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
  png: STATUS_COLORS.violet,
  jpg: STATUS_COLORS.violet,
  jpeg: STATUS_COLORS.violet,
  webp: STATUS_COLORS.violet,
  gif: STATUS_COLORS.violet,
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
  totalBytes: number;
}

export function computeStats(
  assets: AssetItem[],
  indexing: IndexingEntry[],
): AssetStats {
  let indexed = 0;
  let processing = 0;
  let totalBytes = 0;
  for (const a of assets) {
    totalBytes += a.sizeBytes;
    if (a.indexed) {
      indexed += 1;
    } else if (isLiveIndexing(a, indexing)) {
      processing += 1;
    }
  }
  return { total: assets.length, indexed, processing, totalBytes };
}
