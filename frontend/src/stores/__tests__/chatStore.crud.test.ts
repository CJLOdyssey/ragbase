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
  it('初始状态正确', async () => {
    const { useChatStore } = await import('../chatStore');
    const state = useChatStore.getState();
    expect(state.currentRunId).toBeNull();
    expect(state.currentSessionId).toBeNull();
    expect(state.messages).toEqual([]);
    expect(state.status).toBe('idle');
    expect(state.result).toBeNull();
    expect(state.currentRole).toBeNull();
    expect(state.error).toBeNull();
    expect(state.wsStatus).toBe('disconnected');
  });

  it('clearMessages 清空消息与流状态但保留会话 id', async () => {
    const { useChatStore } = await import('../chatStore');
    useChatStore.getState().setStatus('running');
    useChatStore.getState().setWsStatus('connecting');
    useChatStore.setState({
      messages: [
        {
          id: 'm1',
          role: 'user',
          agent_name: '我',
          content: 'hi',
          round_number: 1,
          created_at: '',
        },
      ],
      currentSessionId: 'sess-1',
      streamingId: 'run-1',
    });
    useChatStore.getState().clearMessages();
    const s = useChatStore.getState();
    expect(s.messages).toEqual([]);
    expect(s.status).toBe('idle');
    expect(s.wsStatus).toBe('disconnected');
    expect(s.streamingId).toBeNull();
    expect(s.currentSessionId).toBe('sess-1');
  });

  it('setStatus 更新状态', async () => {
    const { useChatStore } = await import('../chatStore');
    const store = useChatStore.getState();
    store.setStatus('loading');
    expect(useChatStore.getState().status).toBe('loading');
    store.setStatus('running');
    expect(useChatStore.getState().status).toBe('running');
    store.setStatus('completed');
    expect(useChatStore.getState().status).toBe('completed');
    store.setStatus('error');
    expect(useChatStore.getState().status).toBe('error');
  });

  it('setResult 存储结果', async () => {
    const { useChatStore } = await import('../chatStore');
    const result = {
      requirement: 'test',
      pm_document: 'doc',
      code: 'code',
      review: 'review',
      approved: true,
      status: 'converged',
    };
    useChatStore.getState().setResult(result);
    expect(useChatStore.getState().result).toEqual(result);
  });

  it('setError 设置和清除错误', async () => {
    const { useChatStore } = await import('../chatStore');
    useChatStore.getState().setError('出错了');
    expect(useChatStore.getState().error).toBe('出错了');
    useChatStore.getState().setError(null);
    expect(useChatStore.getState().error).toBeNull();
  });

  it('setWsStatus 更新 WebSocket 连接状态', async () => {
    const { useChatStore } = await import('../chatStore');
    useChatStore.getState().setWsStatus('connecting');
    expect(useChatStore.getState().wsStatus).toBe('connecting');
    useChatStore.getState().setWsStatus('connected');
    expect(useChatStore.getState().wsStatus).toBe('connected');
    useChatStore.getState().setWsStatus('reconnecting');
    expect(useChatStore.getState().wsStatus).toBe('reconnecting');
    useChatStore.getState().setWsStatus('disconnected');
    expect(useChatStore.getState().wsStatus).toBe('disconnected');
  });

  describe('addMessage', () => {
    it('添加消息到消息列表', async () => {
      const { useChatStore } = await import('../chatStore');
      useChatStore.getState().addMessage({
        type: 'message',
        role: 'pm',
        agent_name: 'PM',
        content: '测试',
      });
      const state = useChatStore.getState();
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0].role).toBe('pm');
      expect(state.messages[0].content).toBe('测试');
      expect(state.currentRole).toBe('pm');
    });

    it('添加多条消息递增列表', async () => {
      const { useChatStore } = await import('../chatStore');
      useChatStore.getState().addMessage({
        type: 'message',
        role: 'pm',
        agent_name: 'PM',
        content: 'msg1',
      });
      useChatStore.getState().addMessage({
        type: 'message',
        role: 'dev',
        agent_name: 'DEV',
        content: 'msg2',
      });
      expect(useChatStore.getState().messages).toHaveLength(2);
    });
  });

  it('reset 重置所有状态包括 wsStatus', async () => {
    const { useChatStore } = await import('../chatStore');
    useChatStore.getState().setStatus('running');
    useChatStore.getState().setError('error');
    useChatStore.getState().setWsStatus('connected');
    useChatStore.getState().reset();
    const state = useChatStore.getState();
    expect(state.status).toBe('idle');
    expect(state.error).toBeNull();
    expect(state.messages).toEqual([]);
    expect(state.result).toBeNull();
    expect(state.wsStatus).toBe('disconnected');
  });

  describe('setThumbsFeedback', () => {
    it('sets thumbs feedback on a message', async () => {
      const { useChatStore } = await import('../chatStore');
      useChatStore.setState({
        messages: [
          {
            id: 'm1',
            role: 'agent',
            agent_name: 'Agent',
            content: 'test',
            thinking: '',
            round_number: 0,
            created_at: new Date().toISOString(),
          },
          {
            id: 'm2',
            role: 'agent',
            agent_name: 'Agent',
            content: 'other',
            thinking: '',
            round_number: 0,
            created_at: new Date().toISOString(),
          },
        ],
      });

      useChatStore.getState().setThumbsFeedback('m1', 'up');
      const msgs = useChatStore.getState().messages;
      expect(msgs[0].thumbs).toBe('up');
      expect(msgs[1].thumbs).toBeUndefined();
    });

    it('clears thumbs feedback when null', async () => {
      const { useChatStore } = await import('../chatStore');
      useChatStore.setState({
        messages: [
          {
            id: 'm1',
            role: 'agent',
            agent_name: 'Agent',
            content: 'test',
            thinking: '',
            thumbs: 'up' as const,
            round_number: 0,
            created_at: new Date().toISOString(),
          },
        ],
      });

      useChatStore.getState().setThumbsFeedback('m1', null);
      expect(useChatStore.getState().messages[0].thumbs).toBeNull();
    });
  });
});
