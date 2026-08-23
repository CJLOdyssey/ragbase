/**
 * StorageManager — 组合入口 (Facade)
 *
 * 组合 ValidationService + SessionManager，提供统一 API。
 * 消费者通过此入口访问各子服务，无需了解内部结构 (LoD)。
 */
import type { StorageAdapter } from './StorageAdapter';
import { LocalStorageAdapter } from './StorageAdapter';
import { ValidationService, isValidUserId } from './ValidationService';
import { SessionManager, USER_ID_KEY } from './SessionManager';

// ═══════════════════════════════════════════════════════════════════
// 受管理的 localStorage 键
// ═══════════════════════════════════════════════════════════════════

export const STORAGE_KEYS = {
  USER_ID: USER_ID_KEY,
  SELECTED_MODEL: 'ragbase-selected-model',
  RECENT_MODELS: 'ragbase-recent-models',
  CONVERSATIONS: 'ragbase-conversations',
  SESSIONS_CACHE: 'ragbase-sessions-cache',
  SETTINGS: 'ragbase-settings',
  LANGUAGE: 'language',
} as const;

// ═══════════════════════════════════════════════════════════════════
// StorageManager (Facade)
// ═══════════════════════════════════════════════════════════════════

export class StorageManager {
  readonly validation: ValidationService;
  readonly session: SessionManager;
  private storage: StorageAdapter;

  constructor(storage?: StorageAdapter) {
    this.storage = storage ?? new LocalStorageAdapter();
    this.session = new SessionManager(this.storage);
    this.validation = new ValidationService(this.storage);
    this.validation.addRule({ key: USER_ID_KEY, validate: isValidUserId });
  }

  // ── 委托给 ValidationService ──────────────────────────────────

  validateAll(): void {
    this.validation.validateAll();
  }

  // ── 委托给 SessionManager ─────────────────────────────────────

  getUserId(): string {
    return this.session.getUserId();
  }

  setUserId(id: string): void {
    this.session.setUserId(id);
  }

  ensureGuestId(): string {
    return this.session.ensureGuestId();
  }

  clearSession(): void {
    this.session.clearSession();
    this.storage.removeItem(STORAGE_KEYS.SELECTED_MODEL);
    this.storage.removeItem(STORAGE_KEYS.RECENT_MODELS);
    this.storage.removeItem(STORAGE_KEYS.CONVERSATIONS);
    this.storage.removeItem(STORAGE_KEYS.SESSIONS_CACHE);
  }

  // ── 通用键值操作 (LoD: 消费者不应频繁使用) ────────────────────

  get(key: string): string | null {
    return this.storage.getItem(key);
  }

  set(key: string, value: string): void {
    this.storage.setItem(key, value);
  }

  remove(key: string): void {
    this.storage.removeItem(key);
  }
}

// ═══════════════════════════════════════════════════════════════════
// 全局单例
// ═══════════════════════════════════════════════════════════════════

let _instance: StorageManager | null = null;

export function getStorageManager(): StorageManager {
  if (!_instance) _instance = new StorageManager();
  return _instance;
}
