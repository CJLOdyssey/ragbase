import {
  checkAgentLimit,
  checkTeamLimit,
  sanitizeMessageContent,
  validateInput,
  validateName,
  type TranslateFn,
} from '../validation';
import { describe, expect, it } from 'vitest';

// 依赖注入的翻译函数桩：返回与断言一致的中文文案。
const t: TranslateFn = (key, options) => {
  const messages: Record<string, string> = {
    'validation.nameEmpty': '名称不能为空',
    'validation.nameTooLong': `名称不能超过 ${options?.max} 个字符`,
    'validation.nameTooShort': '名称至少需要 1 个字符',
    'validation.nameInvalidChars': '名称包含非法字符 (< > & " \' /)',
    'validation.nameReserved': `"${options?.name}" 是系统保留名称`,
    'validation.nameDuplicate': '名称已存在，请使用其他名称',
    'validation.teamLimit': `最多只能创建 ${options?.max} 个团队`,
    'validation.agentLimit': `每个团队最多 ${options?.max} 个 Agent`,
  };
  return messages[key] ?? key;
};

describe('validateInput', { tags: ['unit'] }, () => {
  it('rejects empty input', () => {
    const result = validateInput('');
    expect(result.valid).toBe(false);
    expect(result.error).toBe('Input cannot be empty');
  });

  it('rejects whitespace-only input', () => {
    const result = validateInput('   ');
    expect(result.valid).toBe(false);
  });

  it('rejects input exceeding max length', () => {
    const long = 'a'.repeat(10001);
    const result = validateInput(long);
    expect(result.valid).toBe(false);
    expect(result.error).toContain('too long');
  });

  it('accepts valid input', () => {
    const result = validateInput('hello world');
    expect(result.valid).toBe(true);
    expect(result.sanitized).toBe('hello world');
  });

  it('strips control characters', () => {
    const result = validateInput('hello\x00world\x1F');
    expect(result.valid).toBe(true);
    expect(result.sanitized).toBe('helloworld');
  });

  it('trims whitespace', () => {
    const result = validateInput('  hello  ');
    expect(result.valid).toBe(true);
    expect(result.sanitized).toBe('hello');
  });
});

describe('sanitizeMessageContent', { tags: ['unit'] }, () => {
  it('passes through normal text', () => {
    expect(sanitizeMessageContent('hello world')).toBe('hello world');
  });

  it('removes null bytes', () => {
    expect(sanitizeMessageContent('hello\x00world')).toBe('helloworld');
  });

  it('removes control characters', () => {
    expect(sanitizeMessageContent('a\x01b\x1Fc')).toBe('abc');
  });

  it('preserves newlines and tabs', () => {
    expect(sanitizeMessageContent('line1\nline2\tindented')).toBe(
      'line1\nline2\tindented',
    );
  });
});

describe('validateName', { tags: ['unit'] }, () => {
  it('returns valid for a standard name', () => {
    expect(validateName(t, 'TestAgent').valid).toBe(true);
  });

  it('rejects empty name', () => {
    const r = validateName(t, '');
    expect(r.valid).toBe(false);
    expect(r.error).toContain('不能为空');
  });

  it('rejects name exceeding 64 chars', () => {
    const r = validateName(t, 'a'.repeat(65));
    expect(r.valid).toBe(false);
    expect(r.error).toContain('不能超过');
  });

  it('rejects dangerous characters', () => {
    const r = validateName(t, '<script>');
    expect(r.valid).toBe(false);
    expect(r.error).toContain('非法字符');
  });

  it('rejects reserved names', () => {
    expect(validateName(t, '新建').valid).toBe(false);
    expect(validateName(t, 'default').valid).toBe(false);
  });

  it('detects duplicate names case-insensitively', () => {
    const r = validateName(t, 'Test', ['test']);
    expect(r.valid).toBe(false);
    expect(r.error).toBe('名称已存在，请使用其他名称');
  });

  it('allows duplicate when editing same item', () => {
    expect(validateName(t, 'Test', ['test'], 'some-id').valid).toBe(true);
  });

  it('allows when editing and only one duplicate exists', () => {
    const r = validateName(t, 'Test', ['test', 'other'], 'some-id');
    expect(r.valid).toBe(true);
  });
});

describe('checkTeamLimit', { tags: ['unit'] }, () => {
  it('allows when under limit', () => {
    expect(checkTeamLimit(t, 49).valid).toBe(true);
  });

  it('rejects when at limit', () => {
    const r = checkTeamLimit(t, 50);
    expect(r.valid).toBe(false);
    expect(r.error).toContain('最多只能创建');
  });
});

describe('checkAgentLimit', { tags: ['unit'] }, () => {
  it('allows when under limit', () => {
    expect(checkAgentLimit(t, 19).valid).toBe(true);
  });

  it('rejects when at limit', () => {
    const r = checkAgentLimit(t, 20);
    expect(r.valid).toBe(false);
    expect(r.error).toContain('最多');
  });
});
