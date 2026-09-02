/**
 * SessionManager — 用户会话管理 (SRP)
 *
 * 只负责：user_id 的读取、写入。
 */
import type { StorageAdapter } from './StorageAdapter';
import { isValidUserId } from './ValidationService';

export const USER_ID_KEY = 'ragbase_user_id';

export class SessionManager {
  constructor(private storage: StorageAdapter) {}

  /** 获取当前 user_id，不存在返回空串 */
  getUserId(): string {
    return this.storage.getItem(USER_ID_KEY) ?? '';
  }

  /** 设置 user_id */
  setUserId(id: string): void {
    this.storage.setItem(USER_ID_KEY, id);
  }

  /** 生成并返回游客 ID（如果尚不存在或无效） */
  ensureGuestId(): string {
    const stored = this.getUserId();
    if (stored && isValidUserId(stored)) return stored;
    const id =
      'u_' +
      Date.now().toString(36) +
      '_' +
      Math.random().toString(36).slice(2, 8);
    this.setUserId(id);
    return id;
  }

  /** 清除会话相关数据 */
  clearSession(): void {
    this.storage.removeItem(USER_ID_KEY);
  }
}
