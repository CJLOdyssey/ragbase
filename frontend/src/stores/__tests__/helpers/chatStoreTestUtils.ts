import type { AppStatus } from '../../../types';
import { vi } from 'vitest';

// Shared mock fns for the chatStore test files. NOTE: plain vi.fn() exports
// (NOT vi.hoisted) — vitest 4 forbids exporting hoisted variables
// ("Cannot export hoisted variable"). Test files reference them from vi.mock
// factories via async dynamic import (see the test files).
export const chatStoreMocks = {
  connectRun: vi.fn(() => vi.fn()),
  disconnectRun: vi.fn(),
  submitRequirement: vi.fn(),
  cancelRun: vi
    .fn()
    .mockResolvedValue({ run_id: 'run-1', status: 'cancelled' }),
  listKeys: vi.fn().mockResolvedValue([
    {
      id: 'key-1',
      is_default: true,
      is_active: true,
      models: ['deepseek-chat'],
    },
  ]),
};

export const chatStoreInitialState = {
  currentRunId: null,
  currentSessionId: null,
  messages: [],
  status: 'idle' as AppStatus,
  result: null,
  currentRole: null,
  error: null,
  wsStatus: 'disconnected' as const,
};

// beforeEach body shared by most chatStore test files (soft reset). chatStore
// is imported dynamically so that importing this module does NOT pull in
// chatStore (and thereby api/client) before the test file's vi.mock factories
// are registered.
export async function resetChatStoreState(): Promise<void> {
  const { useChatStore } = await import('../../chatStore');
  useChatStore.setState(chatStoreInitialState);
}

// Hard reset used by the branch-state tests.
export async function resetChatStoreHard(): Promise<void> {
  const { useChatStore } = await import('../../chatStore');
  useChatStore.getState().reset();
}
