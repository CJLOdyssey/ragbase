import {
  getSessionCache,
  invalidateSessionCache,
  MODEL_STORAGE_KEY,
  persistActiveConvId,
  readActiveConvId,
  readSessionsCache,
  readStoredModel,
  SESSIONS_CACHE_KEY,
  setSessionCache,
  toConversation,
  writeSessionsCache,
} from '../sessionCache';
import { beforeEach, describe, expect, it } from 'vitest';
import type { SessionItem } from '../../types';

const SESSION: SessionItem = {
  id: 's1',
  title: 't',
  kind: 'chat',
  run_count: 2,
  is_pinned: true,
  created_at: '2026-08-01T00:00:00Z',
  updated_at: null,
};

describe('sessionCache', { tags: ['unit'] }, () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('round-trips the sessions cache', () => {
    expect(readSessionsCache()).toEqual([]);
    writeSessionsCache([SESSION]);
    expect(readSessionsCache()).toEqual([SESSION]);
    expect(localStorage.getItem(SESSIONS_CACHE_KEY)).toBe(
      JSON.stringify([SESSION]),
    );
  });

  it('returns [] for corrupt or non-array cache payloads', () => {
    localStorage.setItem(SESSIONS_CACHE_KEY, '{not json');
    expect(readSessionsCache()).toEqual([]);
    localStorage.setItem(SESSIONS_CACHE_KEY, '{"a":1}');
    expect(readSessionsCache()).toEqual([]);
    localStorage.setItem(SESSIONS_CACHE_KEY, 'null');
    expect(readSessionsCache()).toEqual([]);
  });

  it('readStoredModel returns stored value or empty string', () => {
    expect(readStoredModel()).toBe('');
    localStorage.setItem(MODEL_STORAGE_KEY, 'gpt-4');
    expect(readStoredModel()).toBe('gpt-4');
  });

  it('persistActiveConvId sets and removes the active conv key', () => {
    persistActiveConvId('c1');
    expect(readActiveConvId()).toBe('c1');
    persistActiveConvId(null);
    expect(readActiveConvId()).toBeNull();
  });

  it('readActiveConvId returns null when unset', () => {
    expect(readActiveConvId()).toBeNull();
  });

  it('toConversation maps SessionItem with null-safe fallbacks', () => {
    expect(toConversation(SESSION)).toEqual({
      id: 's1',
      title: 't',
      createdAt: '2026-08-01T00:00:00Z',
      updatedAt: '',
      messages: [],
      isPinned: true,
      runCount: 2,
    });
    const sparse = { ...SESSION, is_pinned: undefined, run_count: undefined };
    expect(toConversation(sparse)).toMatchObject({
      isPinned: false,
      runCount: 0,
    });
  });

  it('in-memory session cache get/set/invalidate', () => {
    const entry = { loaded: [], active: 'r1' };
    expect(getSessionCache('c1')).toBeUndefined();
    setSessionCache('c1', entry);
    expect(getSessionCache('c1')).toBe(entry);
    invalidateSessionCache('c1');
    expect(getSessionCache('c1')).toBeUndefined();
    // 空/null 调用不报错
    invalidateSessionCache(null);
    invalidateSessionCache(undefined);
  });
});
