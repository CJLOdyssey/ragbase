import type { ChatMessage } from '../types';

export interface SessionCacheEntry {
  loaded: ChatMessage[];
  active: string | null;
}

const cache = new Map<string, SessionCacheEntry>();

export function getSessionCache(convId: string): SessionCacheEntry | undefined {
  return cache.get(convId);
}

export function setSessionCache(
  convId: string,
  entry: SessionCacheEntry,
): void {
  cache.set(convId, entry);
}

export function invalidateSessionCache(
  convId: string | null | undefined,
): void {
  if (convId) cache.delete(convId);
}
