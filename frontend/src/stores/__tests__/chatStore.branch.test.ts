// NOTE: the helper module must be imported FIRST so its shared mock fns are
// initialized before any vi.mock factory runs. chatStore is only imported
// dynamically (never statically) so no module-load-time mock is triggered
// before this file finishes evaluating.
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  chatStoreMocks,
  resetChatStoreHard,
} from './helpers/chatStoreTestUtils';

vi.mock('../../api/websocket', () => ({
  connectRun: chatStoreMocks.connectRun,
  disconnectRun: chatStoreMocks.disconnectRun,
}));

vi.mock('../../api/client', () => ({
  submitRequirement: chatStoreMocks.submitRequirement,
  cancelRun: chatStoreMocks.cancelRun,
  listKeys: chatStoreMocks.listKeys,
}));

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
