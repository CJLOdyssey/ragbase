import type { AssetItem } from '../../types/assets';
import type { IndexProgress } from '../../api/client/assets';
import { getAssetStatus, getExt, type IndexingEntry } from './assetUtils';

export interface FilterOpts {
  search: string;
  timeFrom: number | null;
  timeTo: number | null;
  formats: string[];
  statuses: string[];
  indexing: IndexingEntry[];
  progressMap: Record<string, IndexProgress>;
  getTime?: (a: AssetItem) => number;
}

function formatDateForSearch(ts: number | null | undefined): string {
  if (!ts) return '';
  try {
    return new Date(ts).toISOString().slice(0, 10);
  } catch {
    return '';
  }
}

function matchSearch(
  a: AssetItem,
  q: string,
  getTime?: (x: AssetItem) => number,
): boolean {
  if (!q) return true;
  const nameHit = a.name.toLowerCase().includes(q);
  if (nameHit) return true;
  const ext = getExt(a.name);
  if (ext && ext.includes(q)) return true;
  if (getTime) {
    const dateStr = formatDateForSearch(getTime(a));
    if (dateStr.includes(q)) return true;
  }
  return false;
}

function matchFormat(a: AssetItem, formats: string[]): boolean {
  if (formats.length === 0) return true;
  return formats.includes(getExt(a.name));
}

function matchStatus(
  a: AssetItem,
  statuses: string[],
  indexing: IndexingEntry[],
  progressMap: Record<string, IndexProgress>,
): boolean {
  if (statuses.length === 0) return true;
  const s = getAssetStatus(a, indexing, progressMap[a.id]);
  return statuses.includes(s);
}

function matchTime(
  a: AssetItem,
  from: number | null,
  to: number | null,
  getTime?: (x: AssetItem) => number,
): boolean {
  if (!getTime) return true;
  if (from === null && to === null) return true;
  const t = getTime(a);
  if (from !== null && t < from) return false;
  if (to !== null && t > to) return false;
  return true;
}

export function filterAssets(
  assets: AssetItem[],
  opts: FilterOpts,
): AssetItem[] {
  const q = opts.search.trim().toLowerCase();
  return assets.filter((a) => {
    if (!matchSearch(a, q, opts.getTime)) return false;
    if (!matchFormat(a, opts.formats)) return false;
    if (!matchStatus(a, opts.statuses, opts.indexing, opts.progressMap))
      return false;
    if (!matchTime(a, opts.timeFrom, opts.timeTo, opts.getTime)) return false;
    return true;
  });
}
