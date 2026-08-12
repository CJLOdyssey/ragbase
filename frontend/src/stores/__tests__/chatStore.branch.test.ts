// NOTE: the helper module must be imported FIRST so its shared mock fns are
// initialized before any vi.mock factory runs. chatStore is only imported
// dynamically (never statically) so no module-load-time mock is triggered
// before this file finishes evaluating.
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  chatStoreMocks,
  resetChatStoreHard,
} from './helpers/chatStoreTestUtils';

vi.mock('../../api/websocket', async () => {
  const h = await import('./helpers/chatStoreTestUtils');
  return {
    connectRun: h.chatStoreMocks.connectRun,
    disconnectRun: h.chatStoreMocks.disconnectRun,
  };
});

vi.mock('../../api/client', async () => {
  const h = await import('./helpers/chatStoreTestUtils');
  return {
    submitRequirement: h.chatStoreMocks.submitRequirement,
    cancelRun: h.chatStoreMocks.cancelRun,
    listKeys: h.chatStoreMocks.listKeys,
  };
});

describe('branch state', () => {
  beforeEach(async () => {
    await resetChatStoreHard();
  });

  it('setActiveRunId updates activeRunId', async () => {
    const { useChatStore } = await import('../chatStore');
    useChatStore.getState().setActiveRunId('run-1');
    expect(useChatStore.getState().activeRunId).toBe('run-1');
    useChatStore.getState().setActiveRunId(null);
    expect(useChatStore.getState().activeRunId).toBeNull();
  });

  it('loadConversation clears activeRunId', async () => {
    const { useChatStore } = await import('../chatStore');
    useChatStore.getState().setActiveRunId('run-1');
    useChatStore.getState().loadConversation([]);
    expect(useChatStore.getState().activeRunId).toBeNull();
  });
});
