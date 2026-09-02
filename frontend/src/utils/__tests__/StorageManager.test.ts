import { describe, it, expect, beforeEach } from 'vitest';
import { StorageManager, STORAGE_KEYS } from '../storage/StorageManager';
import { MemoryStorageAdapter } from '../storage/StorageAdapter';

describe('StorageManager (integration)', () => {
  let adapter: MemoryStorageAdapter;
  let sm: StorageManager;

  beforeEach(() => {
    adapter = new MemoryStorageAdapter();
    sm = new StorageManager(adapter);
  });

  describe('validateAll', () => {
    it('clears invalid USER_ID', () => {
      adapter.setItem('ragbase_user_id', 'admin');
      sm.validateAll();
      expect(adapter.getItem('ragbase_user_id')).toBeNull();
    });

    it('keeps valid u_ prefix ID', () => {
      adapter.setItem('ragbase_user_id', 'u_abc123');
      sm.validateAll();
      expect(adapter.getItem('ragbase_user_id')).toBe('u_abc123');
    });

    it('keeps valid UUID', () => {
      adapter.setItem('ragbase_user_id', 'ab2ce94c-19b6-45d5-b865-ec4c34aa257f');
      sm.validateAll();
      expect(adapter.getItem('ragbase_user_id')).toBe('ab2ce94c-19b6-45d5-b865-ec4c34aa257f');
    });
  });

  describe('ensureGuestId', () => {
    it('returns existing valid ID', () => {
      adapter.setItem('ragbase_user_id', 'u_existing');
      expect(sm.ensureGuestId()).toBe('u_existing');
    });

    it('generates new u_ prefix ID', () => {
      const id = sm.ensureGuestId();
      expect(id.startsWith('u_')).toBe(true);
      expect(adapter.getItem('ragbase_user_id')).toBe(id);
    });

    it('generates new ID when old value is invalid', () => {
      adapter.setItem('ragbase_user_id', 'admin');
      const id = sm.ensureGuestId();
      expect(id.startsWith('u_')).toBe(true);
    });
  });

  describe('session management', () => {
    it('setUserId / getUserId', () => {
      sm.setUserId('test-id');
      expect(sm.getUserId()).toBe('test-id');
    });

    it('clearSession clears session data', () => {
      sm.setUserId('test-id');
      sm.set(STORAGE_KEYS.SELECTED_MODEL, 'model-1');
      sm.set(STORAGE_KEYS.CONVERSATIONS, '[1,2,3]');
      sm.clearSession();
      expect(sm.getUserId()).toBe('');
      expect(adapter.getItem(STORAGE_KEYS.SELECTED_MODEL)).toBeNull();
      expect(adapter.getItem(STORAGE_KEYS.CONVERSATIONS)).toBeNull();
    });
  });

  describe('sub-services accessible', () => {
    it('exposes validation service', () => {
      expect(sm.validation).toBeDefined();
      expect(typeof sm.validation.validateAll).toBe('function');
    });

    it('exposes session manager', () => {
      expect(sm.session).toBeDefined();
      expect(typeof sm.session.getUserId).toBe('function');
    });
  });
});
