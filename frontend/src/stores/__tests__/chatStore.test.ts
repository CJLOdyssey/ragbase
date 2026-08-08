import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AppStatus } from '../../types';

vi.mock('../../api/websocket', () => ({
  connectRun: vi.fn(() => vi.fn()),
  disconnectRun: vi.fn(),
}));

vi.mock('../../api/client', () => ({
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
}));

const initialState = {
  currentRunId: null,
  currentSessionId: null,
  messages: [],
  status: 'idle' as AppStatus,
  result: null,
  currentRole: null,
  error: null,
  wsStatus: 'disconnected' as const,
};

beforeEach(async () => {
  const { useChatStore } = await import('../chatStore');
  useChatStore.setState(initialState);
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
        'conv-1',
        'sess-1',
      );
      const state = useChatStore.getState();
      expect(state.messages).toHaveLength(1);
      expect(state.currentConvId).toBe('conv-1');
      expect(state.currentSessionId).toBe('sess-1');
      expect(state.status).toBe('idle');
      expect(state.wsStatus).toBe('disconnected');
      expect(state.streamingId).toBeNull();
    });

    it('loads conversation without optional params', async () => {
      const { useChatStore } = await import('../chatStore');
      useChatStore.getState().loadConversation([]);
      const state = useChatStore.getState();
      expect(state.currentConvId).toBeNull();
      expect(state.currentSessionId).toBeNull();
    });
  });

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

  describe('switchUserVersion', () => {
    it('switches to next version', async () => {
      const { useChatStore } = await import('../chatStore');
      useChatStore.setState({
        messages: [
          {
            id: 'm1',
            role: 'user',
            agent_name: 'User',
            content: 'v1',
            userVersions: ['v1', 'v2'],
            currentUserVersion: 0,
            round_number: 0,
            created_at: new Date().toISOString(),
          },
        ],
      });

      useChatStore.getState().switchUserVersion('m1', 'next');
      const msg = useChatStore.getState().messages[0];

      expect(msg.content).toBe('v2');
      expect(msg.currentUserVersion).toBe(1);
    });

    it('switches to previous version', async () => {
      const { useChatStore } = await import('../chatStore');
      useChatStore.setState({
        messages: [
          {
            id: 'm1',
            role: 'user',
            agent_name: 'User',
            content: 'v2',
            userVersions: ['v1', 'v2', 'v3'],
            currentUserVersion: 2,
            round_number: 0,
            created_at: new Date().toISOString(),
          },
        ],
      });

      useChatStore.getState().switchUserVersion('m1', 'prev');
      const msg = useChatStore.getState().messages[0];

      expect(msg.content).toBe('v2');
      expect(msg.currentUserVersion).toBe(1);
    });

    it('clamps version at bounds', async () => {
      const { useChatStore } = await import('../chatStore');
      useChatStore.setState({
        messages: [
          {
            id: 'm1',
            role: 'user',
            agent_name: 'User',
            content: 'v1',
            userVersions: ['v1', 'v2'],
            currentUserVersion: 0,
            round_number: 0,
            created_at: new Date().toISOString(),
          },
        ],
      });

      useChatStore.getState().switchUserVersion('m1', 'prev');
      const msg = useChatStore.getState().messages[0];
      expect(msg.currentUserVersion).toBe(0);
    });

    it('ignores messages without versions', async () => {
      const { useChatStore } = await import('../chatStore');
      useChatStore.setState({
        messages: [
          {
            id: 'm1',
            role: 'user',
            agent_name: 'User',
            content: 'old',
            round_number: 0,
            created_at: new Date().toISOString(),
          },
        ],
      });

      useChatStore.getState().switchUserVersion('m1', 'next');
      const msg = useChatStore.getState().messages[0];
      expect(msg.content).toBe('old');
    });
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

describe('branch state', () => {
  beforeEach(async () => {
    const { useChatStore } = await import('../chatStore');
    useChatStore.getState().reset();
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
