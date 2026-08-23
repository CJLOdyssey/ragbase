import { describe, it, expect, beforeEach } from 'vitest';
import { ValidationService, isValidUserId } from '../storage/ValidationService';
import { MemoryStorageAdapter } from '../storage/StorageAdapter';

describe('isValidUserId', () => {
  it('accepts u_ prefix', () => expect(isValidUserId('u_abc')).toBe(true));
  it('accepts guest_ prefix', () => expect(isValidUserId('guest_1')).toBe(true));
  it('accepts UUID', () =>
    expect(isValidUserId('ab2ce94c-19b6-45d5-b865-ec4c34aa257f')).toBe(true));
  it('rejects admin', () => expect(isValidUserId('admin')).toBe(false));
  it('rejects empty string', () => expect(isValidUserId('')).toBe(false));
  it('rejects non-string', () => expect(isValidUserId(123)).toBe(false));
});

describe('ValidationService', () => {
  let storage: MemoryStorageAdapter;
  let svc: ValidationService;

  beforeEach(() => {
    storage = new MemoryStorageAdapter();
    svc = new ValidationService(storage);
  });

  it('clears invalid value for registered rule', () => {
    storage.setItem('user_id', 'admin');
    svc.addRule({ key: 'user_id', validate: isValidUserId });
    svc.validateAll();
    expect(storage.getItem('user_id')).toBeNull();
  });

  it('keeps valid value', () => {
    storage.setItem('user_id', 'u_valid');
    svc.addRule({ key: 'user_id', validate: isValidUserId });
    svc.validateAll();
    expect(storage.getItem('user_id')).toBe('u_valid');
  });

  it('skips null values', () => {
    svc.addRule({ key: 'user_id', validate: isValidUserId });
    svc.validateAll();
    expect(storage.getItem('user_id')).toBeNull();
  });

  it('OCP: multiple rules can be added', () => {
    storage.setItem('a', 'bad');
    storage.setItem('b', 'ok');
    svc.addRule({ key: 'a', validate: (v) => v === 'ok' });
    svc.addRule({ key: 'b', validate: (v) => v === 'ok' });
    svc.validateAll();
    expect(storage.getItem('a')).toBeNull();
    expect(storage.getItem('b')).toBe('ok');
  });
});
