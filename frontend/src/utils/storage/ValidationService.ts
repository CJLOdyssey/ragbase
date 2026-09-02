/**
 * ValidationService — 数据验证 (SRP)
 *
 * 只负责：读取 → 验证 → 清除无效值。
 * 新增规则通过 addRule() 扩展，无需修改现有代码 (OCP)。
 */
import type { StorageAdapter } from './StorageAdapter';
import Logger from '../logger';

// ═══════════════════════════════════════════════════════════════════
// 内置验证规则
// ═══════════════════════════════════════════════════════════════════

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const VALID_ID_PREFIXES = ['u_', 'guest_'];

export function isValidUserId(v: unknown): v is string {
  if (typeof v !== 'string' || v.length === 0) return false;
  if (UUID_RE.test(v)) return true;
  return VALID_ID_PREFIXES.some((p) => v.startsWith(p));
}

// ═══════════════════════════════════════════════════════════════════
// ValidationService
// ═══════════════════════════════════════════════════════════════════

export interface ValidationRule {
  key: string;
  validate: (value: string) => boolean;
}

export class ValidationService {
  private rules: ValidationRule[] = [];

  constructor(private storage: StorageAdapter) {}

  /** OCP: 运行时注册新规则，无需修改类 */
  addRule(rule: ValidationRule): this {
    this.rules.push(rule);
    return this;
  }

  /** 遍历所有规则，清除无效值 */
  validateAll(): void {
    for (const { key, validate } of this.rules) {
      const raw = this.storage.getItem(key);
      if (raw === null) continue;
      if (validate(raw)) continue;
      Logger.warn('[Storage] clearing invalid key=%s value=%s', key, raw.slice(0, 20));
      this.storage.removeItem(key);
    }
  }
}
