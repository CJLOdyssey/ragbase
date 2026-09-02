import { useEffect, useMemo, useState } from 'react';
import type { AssetItem } from '../../types/assets';
import type { IndexProgress } from '../../api/client/assets';
import {
  computeStats,
  getAssetStatus,
  resolveTimeRange,
  type IndexingEntry,
  type TimeRange,
} from './assetUtils';
import { filterAssets } from './useAssetFilters';

interface SortCtx {
  indexing: IndexingEntry[];
  progressMap: Record<string, IndexProgress>;
}

const getTime = (a: AssetItem) =>
  a.updatedAt ? new Date(a.updatedAt).getTime() : 0;
const assetStatus = (a: AssetItem, ctx: SortCtx) =>
  getAssetStatus(a, ctx.indexing, ctx.progressMap[a.id]);

const SORTERS: Record<
  string,
  (a: AssetItem, b: AssetItem, ctx: SortCtx) => number
> = {
  name: (a, b) => a.name.localeCompare(b.name),
  format: (a, b) =>
    (a.name.split('.').pop() || '').localeCompare(
      b.name.split('.').pop() || '',
    ),
  size: (a, b) => a.sizeBytes - b.sizeBytes,
  status: (a, b, ctx) => assetStatus(a, ctx).localeCompare(assetStatus(b, ctx)),
  chunks: (a, b) => (a.chunkCount ?? -1) - (b.chunkCount ?? -1),
  updated: (a, b) => getTime(a) - getTime(b),
  usageCount: (a, b) =>
    a.usageCount !== b.usageCount
      ? a.usageCount - b.usageCount
      : getTime(a) - getTime(b),
  usage: (a, b) =>
    a.usageCount !== b.usageCount
      ? a.usageCount - b.usageCount
      : getTime(a) - getTime(b),
  lastUsed: (a, b) =>
    getTime(a) !== getTime(b)
      ? getTime(a) - getTime(b)
      : a.usageCount - b.usageCount,
  last_used: (a, b) =>
    getTime(a) !== getTime(b)
      ? getTime(a) - getTime(b)
      : a.usageCount - b.usageCount,
};

export function useAssetSelection(
  assets: AssetItem[],
  indexing: IndexingEntry[],
  progressMap: Record<string, IndexProgress>,
) {
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [formats, setFormats] = useState<string[]>([]);
  const [statuses, setStatuses] = useState<string[]>([]);
  // 知识库筛选：'all' | 'unassigned' | <kbId>
  const [kbFilter, setKbFilter] = useState('all');
  const [timeRange, setTimeRange] = useState<TimeRange>('all');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  // 默认按点击排序：点击次数 + 最近一次点击 均从高到低（全栈对齐 backend order_by）
  const [sortField, setSortField] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const totalStats = useMemo(
    () => computeStats(assets, indexing, progressMap),
    [assets, indexing, progressMap],
  );
  const timeBounds = useMemo(
    () => resolveTimeRange(timeRange, customFrom, customTo),
    [timeRange, customFrom, customTo],
  );

  const getUpdatedTime = (a: AssetItem) =>
    a.updatedAt ? new Date(a.updatedAt).getTime() : 0;

  const filterWith = (searchValue: string) =>
    filterAssets(assets, {
      search: searchValue,
      timeFrom: timeBounds.from,
      timeTo: timeBounds.to,
      formats,
      statuses,
      kbFilter,
      indexing,
      progressMap,
      getTime: getUpdatedTime,
    });

  const filteredAssets = useMemo(
    () => filterWith(debouncedSearch),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      assets,
      debouncedSearch,
      timeBounds,
      formats,
      statuses,
      kbFilter,
      indexing,
      progressMap,
    ],
  );

  const stats = useMemo(
    () => computeStats(filteredAssets, indexing, progressMap),
    [filteredAssets, indexing, progressMap],
  );

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const a of assets) {
      const s = getAssetStatus(a, indexing, progressMap[a.id]);
      counts[s] = (counts[s] ?? 0) + 1;
    }
    return counts;
  }, [assets, indexing, progressMap]);

  const sortedAssets = useMemo(() => {
    // 默认：最新一次点击优先，其次点击次数从高到低（全栈对齐 backend）
    if (!sortField) {
      return [...filteredAssets].sort((a, b) => {
        const ta = getTime(a);
        const tb = getTime(b);
        if (tb !== ta) return tb - ta;
        return b.usageCount - a.usageCount;
      });
    }
    const dir = sortDir === 'asc' ? 1 : -1;
    const ctx: SortCtx = { indexing, progressMap };
    const cmp = SORTERS[sortField];
    if (!cmp) return filteredAssets;
    return [...filteredAssets].sort((a, b) => dir * cmp(a, b, ctx));
  }, [filteredAssets, sortField, sortDir, indexing, progressMap]);

  const handleSort = (field: string) => {
    if (sortField !== field) {
      setSortField(field);
      setSortDir('asc');
      return;
    }
    if (sortDir === 'asc') {
      setSortDir('desc');
      return;
    }
    // desc -> default
    setSortField(null);
    setSortDir('asc');
  };

  const selectAllChecked =
    filteredAssets.length > 0 &&
    filteredAssets.every((a) => selectedIds.has(a.id));
  const handleSelectAll = (checked: boolean) => {
    if (checked)
      // 用即时 search 计算选中集（而非 300ms 防抖后的旧列表）：输入关键词
      // 后立刻全选，否则会按防抖窗口前的旧过滤结果勾选无关资产。
      setSelectedIds(new Set(filterWith(search).map((a) => a.id)));
    else setSelectedIds(new Set());
  };
  const handleSelectOne = (id: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };
  const clearAll = () => {
    setSearch('');
    setFormats([]);
    setStatuses([]);
    setKbFilter('all');
    setTimeRange('all');
    setCustomFrom('');
    setCustomTo('');
    setSelectedIds(new Set());
  };

  return {
    search,
    setSearch,
    debouncedSearch,
    formats,
    setFormats,
    statuses,
    setStatuses,
    kbFilter,
    setKbFilter,
    timeRange,
    setTimeRange,
    customFrom,
    setCustomFrom,
    customTo,
    setCustomTo,
    selectedIds,
    setSelectedIds,
    sortField,
    sortDir,
    stats,
    totalStats,
    filteredAssets,
    sortedAssets,
    statusCounts,
    timeBounds,
    selectAllChecked,
    handleSelectAll,
    handleSelectOne,
    handleSort,
    clearAll,
  };
}
