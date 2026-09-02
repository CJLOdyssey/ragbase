import type { AssetItem } from '../../../types/assets';
import {
  computeStats,
  getAssetStatus,
  type IndexingEntry,
} from '../assetUtils';
import { describe, expect, it } from 'vitest';

const DOC: AssetItem = {
  id: 'a1',
  name: 'hello.pdf',
  assetType: 'document',
  sizeBytes: 47,
  usageCount: 0,
  indexed: false,
};

const NO_INDEXING: IndexingEntry[] = [];

describe('getAssetStatus — persisted indexError', () => {
  it('reports failed for an asset with a persisted indexError', () => {
    expect(
      getAssetStatus(
        { ...DOC, indexError: 'startxref not found' },
        NO_INDEXING,
      ),
    ).toBe('failed');
  });

  it('still reports pending when no error and no progress', () => {
    expect(getAssetStatus(DOC, NO_INDEXING)).toBe('pending');
  });

  it('live retry wins over a stale persisted error (processing)', () => {
    const live: IndexingEntry[] = [{ id: 'a1', deadline: Date.now() + 60_000 }];
    expect(getAssetStatus({ ...DOC, indexError: 'old failure' }, live)).toBe(
      'processing',
    );
  });

  it('indexed beats a stale persisted error (retry succeeded)', () => {
    expect(
      getAssetStatus(
        { ...DOC, indexed: true, indexError: 'old failure' },
        NO_INDEXING,
      ),
    ).toBe('indexed');
  });
});

describe('computeStats — persisted indexError counts as failed', () => {
  it('counts indexError assets as failed without progressMap', () => {
    const stats = computeStats(
      [
        { ...DOC, id: 'a1', indexError: 'boom' },
        { ...DOC, id: 'a2' },
      ],
      NO_INDEXING,
    );
    expect(stats.failed).toBe(1);
    expect(stats.pending).toBe(1);
  });
});
