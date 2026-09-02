// NOTE: the helper module must be imported FIRST so its shared mock fns are
// initialized before any vi.mock factory runs. chatStore is only imported
// dynamically (never statically) so no module-load-time mock is triggered
// before this file finishes evaluating.
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  chatStoreMocks as _chatStoreMocks,
  resetChatStoreState,
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

beforeEach(async () => {
  await resetChatStoreState();
});

describe('chatStore', { tags: ['unit'] }, () => {
  describe('cancelRun', () => {
    it('disconnects, cancels backend and clears run state', async () => {
      const { useChatStore } = await import('../chatStore');
      const { cancelRun } = await import('../../api/client');
      useChatStore.setState({
        currentRunId: 'run-1',
        streamingId: 'stream-1',
        status: 'running',
      });
      useChatStore.getState().cancelRun();
      await vi.waitFor(() => {
        expect(cancelRun).toHaveBeenCalledWith('run-1');
      });
      const state = useChatStore.getState();
      expect(state.currentRunId).toBeNull();
      expect(state.streamingId).toBeNull();
      expect(state.status).toBe('idle');
      expect(state.wsStatus).toBe('disconnected');
      expect(state.interruptedMessageId).toBe('stream-1');
    });
  });

  describe('submitRequirement', () => {
    it('提交需求时添加用户消息到列表', async () => {
      const client = await import('../../api/client');
      (client.submitRequirement as ReturnType<typeof vi.fn>).mockResolvedValue({
        run_id: 'run-1',
        status: 'running',
      });
      const { submitRequirement } = await import('../chatStore');
      await submitRequirement('测试需求');
      const state = (await import('../chatStore')).useChatStore.getState();
      expect(state.status).toBe('running');
      expect(state.currentRunId).toBe('run-1');
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0].role).toBe('user');
      expect(state.messages[0].agent_name).toBe('我');
      expect(state.messages[0].content).toBe('测试需求');
      expect(state.error).toBeNull();
    });

    it('提交失败时保留用户消息并设置 wsStatus 为 disconnected', async () => {
      const client = await import('../../api/client');
      (client.submitRequirement as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('API Error'),
      );
      const { submitRequirement } = await import('../chatStore');
      await submitRequirement('test');
      const state = (await import('../chatStore')).useChatStore.getState();
      expect(state.status).toBe('error');
      expect(state.error).toBe('API Error');
      expect(state.wsStatus).toBe('disconnected');
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0].role).toBe('user');
    });

    it('无可用 API Key 时返回引导提示', async () => {
      const client = await import('../../api/client');
      (client.submitRequirement as ReturnType<typeof vi.fn>).mockClear();
      (client.listKeys as ReturnType<typeof vi.fn>).mockResolvedValue([]);
      const { submitRequirement } = await import('../chatStore');
      await submitRequirement('测试需求');
      const state = (await import('../chatStore')).useChatStore.getState();
      expect(state.status).toBe('error');
      expect(state.error).toBe('请先在设置中配置 API Key');
      expect(state.wsStatus).toBe('disconnected');
      expect(client.submitRequirement).not.toHaveBeenCalled();
    });
  });
});
