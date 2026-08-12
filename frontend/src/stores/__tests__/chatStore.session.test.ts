// NOTE: the helper module must be imported FIRST so its shared mock fns are
// initialized before any vi.mock factory runs. chatStore is only imported
// dynamically (never statically) so no module-load-time mock is triggered
// before this file finishes evaluating.
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  chatStoreMocks,
  resetChatStoreState,
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

beforeEach(async () => {
  await resetChatStoreState();
});

describe('chatStore', { tags: ['unit'] }, () => {
  describe('restoreSession', () => {
    it('restores session state with messages', async () => {
      const { useChatStore } = await import('../chatStore');
      useChatStore.getState().restoreSession(
        'sess-1',
        'run-1',
        [
          {
            id: 'm1',
            role: 'user',
            agent_name: '我',
            content: 'hello',
            round_number: 0,
            created_at: new Date().toISOString(),
          },
        ],
        null,
        'completed',
      );
      const state = useChatStore.getState();
      expect(state.currentSessionId).toBe('sess-1');
      expect(state.currentRunId).toBe('run-1');
      expect(state.messages).toHaveLength(1);
      expect(state.status).toBe('completed');
      expect(state.currentRole).toBe('user');
      expect(state.error).toBeNull();
    });
  });

  describe('loadConversation', () => {
    it('loads conversation and clears run state', async () => {
      const { useChatStore } = await import('../chatStore');
      useChatStore.setState({ currentRunId: 'old-run', status: 'running' });
      useChatStore.getState().loadConversation(
        [
          {
            id: 'm1',
            role: 'user',
            agent_name: '我',
            content: 'hi',
            round_number: 0,
            created_at: new Date().toISOString(),
          },
        ],
        'sess-1',
      );
      const state = useChatStore.getState();
      expect(state.messages).toHaveLength(1);
      expect(state.currentSessionId).toBe('sess-1');
      expect(state.status).toBe('idle');
      expect(state.wsStatus).toBe('disconnected');
      expect(state.streamingId).toBeNull();
    });

    it('loads conversation without optional params', async () => {
      const { useChatStore } = await import('../chatStore');
      useChatStore.getState().loadConversation([]);
      const state = useChatStore.getState();
      expect(state.currentSessionId).toBeNull();
    });
  });

  describe('resolveVersionTargets', () => {
    function makeMsg(overrides: Record<string, unknown>) {
      return {
        id: 'm1',
        role: 'agent',
        agent_name: 'Agent',
        content: 'c',
        round_number: 0,
        created_at: new Date().toISOString(),
        ...overrides,
      };
    }

    it('resolveUserVersionTarget returns target runId and clamps', async () => {
      const { useChatStore } = await import('../chatStore');
      useChatStore.setState({
        messages: [
          makeMsg({
            userVersions: ['v1', 'v2'],
            versionRunIds: ['r1', 'r2'],
            currentUserVersion: 1,
          }),
        ],
      });
      expect(
        useChatStore.getState().resolveUserVersionTarget('m1', 'prev'),
      ).toBe('r1');
      expect(
        useChatStore.getState().resolveUserVersionTarget('m1', 'next'),
      ).toBeNull(); // 越界夹取 → 无变化
    });

    it('resolveAnswerVersionTarget returns target runId', async () => {
      const { useChatStore } = await import('../chatStore');
      useChatStore.setState({
        messages: [
          makeMsg({
            answerVersions: ['a1', 'a2'],
            answerRunIds: ['r1', 'r2'],
            currentAnswerVersion: 0,
          }),
        ],
      });
      expect(
        useChatStore.getState().resolveAnswerVersionTarget('m1', 'next'),
      ).toBe('r2');
    });

    it('returns null for messages without versions', async () => {
      const { useChatStore } = await import('../chatStore');
      useChatStore.setState({
        messages: [makeMsg({})],
      });
      expect(
        useChatStore.getState().resolveUserVersionTarget('m1', 'next'),
      ).toBeNull();
      expect(
        useChatStore.getState().resolveAnswerVersionTarget('m1', 'next'),
      ).toBeNull();
    });
  });
});
