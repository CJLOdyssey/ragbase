import { describe, it, expect, beforeEach } from 'vitest';
import { SessionManager } from '../storage/SessionManager';
import { MemoryStorageAdapter } from '../storage/StorageAdapter';

describe('SessionManager', () => {
  let storage: MemoryStorageAdapter;
  let sm: SessionManager;

  beforeEach(() => {
    storage = new MemoryStorageAdapter();
    sm = new SessionManager(storage);
  });

  describe('getUserId', () => {
    it('returns empty string when not set', () => {
      expect(sm.getUserId()).toBe('');
    });

    it('returns stored value', () => {
      storage.setItem('ragbase_user_id', 'u_test');
      expect(sm.getUserId()).toBe('u_test');
    });
  });

  describe('setUserId', () => {
    it('stores value', () => {
      sm.setUserId('u_new');
      expect(storage.getItem('ragbase_user_id')).toBe('u_new');
    });
  });

  describe('ensureGuestId', () => {
    it('returns existing valid ID', () => {
      storage.setItem('ragbase_user_id', 'u_existing');
      expect(sm.ensureGuestId()).toBe('u_existing');
    });

    it('generates new ID when missing', () => {
      const id = sm.ensureGuestId();
      expect(id.startsWith('u_')).toBe(true);
      expect(storage.getItem('ragbase_user_id')).toBe(id);
    });

    it('generates new ID when invalid', () => {
      storage.setItem('ragbase_user_id', 'admin');
      const id = sm.ensureGuestId();
      expect(id.startsWith('u_')).toBe(true);
    });
  });

  describe('clearSession', () => {
    it('removes user_id', () => {
      sm.setUserId('u_test');
      sm.clearSession();
      expect(sm.getUserId()).toBe('');
    });
  });
});
