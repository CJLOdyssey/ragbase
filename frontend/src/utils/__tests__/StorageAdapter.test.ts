import { describe, it, expect, beforeEach } from 'vitest';
import { MemoryStorageAdapter } from '../storage/StorageAdapter';

describe('MemoryStorageAdapter', () => {
  let adapter: MemoryStorageAdapter;

  beforeEach(() => {
    adapter = new MemoryStorageAdapter();
  });

  it('getItem returns null for missing key', () => {
    expect(adapter.getItem('missing')).toBeNull();
  });

  it('setItem / getItem round-trip', () => {
    adapter.setItem('k', 'v');
    expect(adapter.getItem('k')).toBe('v');
  });

  it('removeItem deletes key', () => {
    adapter.setItem('k', 'v');
    adapter.removeItem('k');
    expect(adapter.getItem('k')).toBeNull();
  });

  it('clear removes all entries', () => {
    adapter.setItem('a', '1');
    adapter.setItem('b', '2');
    adapter.clear();
    expect(adapter.getItem('a')).toBeNull();
    expect(adapter.getItem('b')).toBeNull();
  });
});
