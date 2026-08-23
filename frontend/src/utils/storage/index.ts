// 接口 + 实现 (DIP)
export type { StorageAdapter } from './StorageAdapter';
export { LocalStorageAdapter, MemoryStorageAdapter } from './StorageAdapter';

// 验证 (SRP + OCP)
export { ValidationService, isValidUserId } from './ValidationService';
export type { ValidationRule } from './ValidationService';

// 会话管理 (SRP)
export { SessionManager, USER_ID_KEY } from './SessionManager';

// 组合入口 (Facade)
export { StorageManager, STORAGE_KEYS, getStorageManager } from './StorageManager';
