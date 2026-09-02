// IndexedDB wrapper for caching RAG retrieval results
// Uses native IndexedDB API (no external library needed)

const DB_NAME = 'ragbase-cache';
const DB_VERSION = 1;
const STORE_EMBEDDINGS = 'embeddings';
const STORE_RETRIEVAL = 'retrieval-results';
const TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

function hashQuery(query: string): string {
  // Simple hash for cache key
  let hash = 0;
  for (let i = 0; i < query.length; i++) {
    const char = query.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0;
  }
  return `q_${hash}_${query.length}`;
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_EMBEDDINGS)) {
        db.createObjectStore(STORE_EMBEDDINGS, { keyPath: 'key' });
      }
      if (!db.objectStoreNames.contains(STORE_RETRIEVAL)) {
        db.createObjectStore(STORE_RETRIEVAL, { keyPath: 'key' });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export interface CachedRetrieval {
  key: string;
  query: string;
  results: unknown[];
  timestamp: number;
}

export async function getCachedRetrieval(query: string): Promise<unknown[] | null> {
  try {
    const db = await openDB();
    return new Promise((resolve) => {
      const tx = db.transaction(STORE_RETRIEVAL, 'readonly');
      const store = tx.objectStore(STORE_RETRIEVAL);
      const request = store.get(hashQuery(query));
      request.onsuccess = () => {
        const entry = request.result as CachedRetrieval | undefined;
        if (entry && Date.now() - entry.timestamp < TTL_MS) {
          resolve(entry.results);
        } else {
          resolve(null);
        }
      };
      request.onerror = () => resolve(null);
    });
  } catch {
    return null;
  }
}

export async function setCachedRetrieval(query: string, results: unknown[]): Promise<void> {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_RETRIEVAL, 'readwrite');
    const store = tx.objectStore(STORE_RETRIEVAL);
    store.put({
      key: hashQuery(query),
      query,
      results,
      timestamp: Date.now(),
    } as CachedRetrieval);
  } catch {
    // non-fatal
  }
}

export async function clearExpiredCache(): Promise<void> {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_RETRIEVAL, 'readwrite');
    const store = tx.objectStore(STORE_RETRIEVAL);
    const request = store.getAll();
    request.onsuccess = () => {
      const entries = request.result as CachedRetrieval[];
      const now = Date.now();
      for (const entry of entries) {
        if (now - entry.timestamp > TTL_MS) {
          store.delete(entry.key);
        }
      }
    };
  } catch {
    // non-fatal
  }
}
