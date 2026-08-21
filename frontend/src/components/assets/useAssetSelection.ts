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

export function useAssetSelection(
  assets: AssetItem[],
  indexing: IndexingEntry[],
  progressMap: Record<string, IndexProgress>,
) {
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [formats, setFormats] = useState<string[]>([]);
  const [statuses, setStatuses] = useState<string[]>([]);
  const [timeRange, setTimeRange] = useState<TimeRange>('all');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [sortField, setSortField] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

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

  const filteredAssets = useMemo(
    () =>
      filterAssets(assets, {
        search: debouncedSearch,
        timeFrom: timeBounds.from,
        timeTo: timeBounds.to,
        formats,
        statuses,
        indexing,
        progressMap,
      }),
    [
      assets,
      debouncedSearch,
      timeBounds,
      formats,
      statuses,
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
    if (!sortField) return filteredAssets;
    const dir = sortDir === 'asc' ? 1 : -1;
    return [...filteredAssets].sort((a, b) => {
      if (sortField === 'name') return dir * a.name.localeCompare(b.name);
      if (sortField === 'format')
        return (
          dir *
          (a.name.split('.').pop() || '').localeCompare(
            b.name.split('.').pop() || '',
          )
        );
      if (sortField === 'size') return dir * (a.sizeBytes - b.sizeBytes);
      if (sortField === 'status') {
        const sa = a.indexed ? 'indexed' : 'pending';
        const sb = b.indexed ? 'indexed' : 'pending';
        return dir * sa.localeCompare(sb);
      }
      return 0;
    });
  }, [filteredAssets, sortField, sortDir]);

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
    if (checked) setSelectedIds(new Set(filteredAssets.map((a) => a.id)));
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
