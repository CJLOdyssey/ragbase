import { describe, it, expect, vi, beforeEach } from 'vitest';

const { mockLogger } = vi.hoisted(() => ({
  mockLogger: {
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  },
}));

vi.mock('../logger', () => mockLogger);

import { installGlobalErrorHandlers } from '../errorHandler';

describe('installGlobalErrorHandlers', { tags: ['unit'] }, () => {
  beforeEach(() => {
    vi.resetAllMocks();
    window.onerror = null;
    window.onunhandledrejection = null;
  });

  it('sets window.onerror handler', () => {
    installGlobalErrorHandlers();
    expect(window.onerror).toBeDefined();
    const error = new Error('test error');
    const result = window.onerror?.('test message', 'test.js', 10, 5, error);
    expect(result).toBe(false);
    expect(mockLogger.error).toHaveBeenCalledWith('Uncaught error', {
      message: 'test message',
      source: 'test.js',
      lineno: 10,
      colno: 5,
      error,
    });
  });

  it('sets window.onunhandledrejection handler', () => {
    installGlobalErrorHandlers();
    expect(window.onunhandledrejection).toBeDefined();
  });

  it('is safe to call multiple times', () => {
    installGlobalErrorHandlers();
    installGlobalErrorHandlers();
    expect(window.onerror).toBeDefined();
  });

  it('handles unhandled rejection with a reason that has a message', () => {
    installGlobalErrorHandlers();
    const event = { reason: new Error('network failure'), preventDefault: vi.fn() } as unknown as PromiseRejectionEvent;
    window.onunhandledrejection?.(event);
    expect(mockLogger.error).toHaveBeenCalledWith('Unhandled promise rejection', { reason: event.reason });
  });

  it('prevents default for Transition was skipped rejection', () => {
    installGlobalErrorHandlers();
    const event = { reason: new Error('Transition was skipped'), preventDefault: vi.fn() } as unknown as PromiseRejectionEvent;
    window.onunhandledrejection?.(event);
    expect(event.preventDefault).toHaveBeenCalled();
    expect(mockLogger.error).not.toHaveBeenCalled();
  });

  it('prevents default for Transition was aborted rejection', () => {
    installGlobalErrorHandlers();
    const event = { reason: new Error('Transition was aborted'), preventDefault: vi.fn() } as unknown as PromiseRejectionEvent;
    window.onunhandledrejection?.(event);
    expect(event.preventDefault).toHaveBeenCalled();
    expect(mockLogger.error).not.toHaveBeenCalled();
  });

  it('handles rejection with string reason (no message property)', () => {
    installGlobalErrorHandlers();
    const event = { reason: 'some string error', preventDefault: vi.fn() } as unknown as PromiseRejectionEvent;
    window.onunhandledrejection?.(event);
    expect(mockLogger.error).toHaveBeenCalledWith('Unhandled promise rejection', { reason: 'some string error' });
  });

  it('handles rejection with null reason', () => {
    installGlobalErrorHandlers();
    const event = { reason: null, preventDefault: vi.fn() } as unknown as PromiseRejectionEvent;
    window.onunhandledrejection?.(event);
    expect(mockLogger.error).toHaveBeenCalledWith('Unhandled promise rejection', { reason: null });
  });

  it('handles rejection with undefined reason', () => {
    installGlobalErrorHandlers();
    const event = { reason: undefined, preventDefault: vi.fn() } as unknown as PromiseRejectionEvent;
    window.onunhandledrejection?.(event);
    expect(mockLogger.error).toHaveBeenCalledWith('Unhandled promise rejection', { reason: undefined });
  });

  it('returns early when window is undefined (SSR guard)', () => {
    const desc = Object.getOwnPropertyDescriptor(globalThis, 'window');
    if (!desc?.configurable) return;
    const origWindow = globalThis.window;
    delete globalThis.window;
    installGlobalErrorHandlers();
    globalThis.window = origWindow;
  });

  it('returns false from onerror', () => {
    installGlobalErrorHandlers();
    const result = window.onerror?.('msg', '', 0, 0, null);
    expect(result).toBe(false);
  });
});
