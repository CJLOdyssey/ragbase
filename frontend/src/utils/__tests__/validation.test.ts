import { describe, it, expect } from 'vitest';
import { validateInput, sanitizeMessageContent, validateName, checkTeamLimit, checkAgentLimit } from '../validation';

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
    expect(sanitizeMessageContent('line1\nline2\tindented')).toBe('line1\nline2\tindented');
  });
});

describe('validateName', { tags: ['unit'] }, () => {
  it('returns valid for a standard name', () => {
    expect(validateName('TestAgent').valid).toBe(true);
  });

  it('rejects empty name', () => {
    const r = validateName('');
    expect(r.valid).toBe(false);
    expect(r.error).toContain('不能为空');
  });

  it('rejects name exceeding 64 chars', () => {
    const r = validateName('a'.repeat(65));
    expect(r.valid).toBe(false);
    expect(r.error).toContain('不能超过');
  });

  it('rejects dangerous characters', () => {
    const r = validateName('<script>');
    expect(r.valid).toBe(false);
    expect(r.error).toContain('非法字符');
  });

  it('rejects reserved names', () => {
    expect(validateName('新建').valid).toBe(false);
    expect(validateName('default').valid).toBe(false);
  });

  it('detects duplicate names case-insensitively', () => {
    const r = validateName('Test', ['test']);
    expect(r.valid).toBe(false);
    expect(r.error).toBe('名称已存在，请使用其他名称');
  });

  it('allows duplicate when editing same item', () => {
    expect(validateName('Test', ['test'], 'some-id').valid).toBe(true);
  });

  it('allows when editing and only one duplicate exists', () => {
    const r = validateName('Test', ['test', 'other'], 'some-id');
    expect(r.valid).toBe(true);
  });
});

describe('checkTeamLimit', { tags: ['unit'] }, () => {
  it('allows when under limit', () => {
    expect(checkTeamLimit(49).valid).toBe(true);
  });

  it('rejects when at limit', () => {
    const r = checkTeamLimit(50);
    expect(r.valid).toBe(false);
    expect(r.error).toContain('最多只能创建');
  });
});

describe('checkAgentLimit', { tags: ['unit'] }, () => {
  it('allows when under limit', () => {
    expect(checkAgentLimit(19).valid).toBe(true);
  });

  it('rejects when at limit', () => {
    const r = checkAgentLimit(20);
    expect(r.valid).toBe(false);
    expect(r.error).toContain('最多');
  });
});
