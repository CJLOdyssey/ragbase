import type { ChatMessage, SessionItem } from '../types';
import type { Conversation } from '../types/studio';

export interface SessionCacheEntry {
  loaded: ChatMessage[];
  active: string | null;
}

export const SESSIONS_CACHE_KEY = 'ragbase-sessions-cache';
export const MODEL_STORAGE_KEY = 'ragbase-selected-model';
export const ACTIVE_CONV_KEY = 'ragbase-active-conv-id';
export const MODEL_CHANGED_EVENT = 'ragbase-model-changed';

// 会话列表渲染缓存：首帧先用本地缓存渲染（刷新丝滑，不等 auth 链），
// 后端列表返回后刷新覆盖（localStorage 会话管理）。
export function readSessionsCache(): SessionItem[] {
  try {
    const raw = localStorage.getItem(SESSIONS_CACHE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function writeSessionsCache(items: SessionItem[]): void {
  try {
    // 乐观占位（temp）不落盘：刷新后以 server 为准
    localStorage.setItem(
      SESSIONS_CACHE_KEY,
      JSON.stringify(items.filter((s) => !s.temp)),
    );
  } catch {
    // non-fatal
  }
}

export function readStoredModel(): string {
  try {
    return localStorage.getItem(MODEL_STORAGE_KEY) || '';
  } catch {
    return '';
  }
}

export function readActiveConvId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_CONV_KEY);
  } catch {
    return null;
  }
}

export function persistActiveConvId(convId: string | null): void {
  try {
    if (convId) localStorage.setItem(ACTIVE_CONV_KEY, convId);
    else localStorage.removeItem(ACTIVE_CONV_KEY);
  } catch {
    // non-fatal
  }
}

export function toConversation(s: SessionItem): Conversation {
  return {
    id: s.id,
    title: s.title,
    createdAt: s.created_at || '',
    updatedAt: s.updated_at || '',
    messages: [],
    isPinned: s.is_pinned ?? false,
    runCount: s.run_count ?? 0,
  };
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
