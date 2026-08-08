import {
  continueGeneration,
  editMessage,
  regenerateMessage,
  retry,
} from '../chatActions';
import { useChatStore } from '../chatStore';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ChatMessage } from '../../types';

const { mockListKeys, mockSubmitReq, mockResumeRun } = vi.hoisted(() => ({
  mockListKeys: vi.fn().mockResolvedValue([
    {
      id: 'key-1',
      is_default: true,
      is_active: true,
      models: ['deepseek-chat'],
    },
  ]),
  mockSubmitReq: vi.fn().mockResolvedValue({
    run_id: 'run-1',
    status: 'running',
    session_id: 'sess-1',
  }),
  mockResumeRun: vi.fn().mockResolvedValue({
    run_id: 'run-2',
    status: 'running',
    session_id: 'sess-1',
  }),
}));

vi.mock('../../api/websocket', () => ({
  connectRun: vi.fn(() => vi.fn()),
  disconnectRun: vi.fn(),
}));

vi.mock('../../api/client', () => ({
  submitRequirement: mockSubmitReq,
  resumeRun: mockResumeRun,
  listKeys: mockListKeys,
  listAgents: vi.fn().mockResolvedValue([]),
}));

vi.mock('../chatStreaming', () => ({
  createStreamHandler: vi.fn(() => vi.fn()),
}));

function makeMsg(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 'msg-1',
    role: 'user' as const,
    agent_name: '\u6211',
    content: 'test content',
    round_number: 0,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

const initialState = {
  currentRunId: null as string | null,
  activeRunId: null as string | null,
  currentSessionId: null as string | null,
  currentConvId: null as string | null,
  messages: [] as ChatMessage[],
  status: 'idle' as const,
  result: null,
  currentRole: null as string | null,
  error: null as string | null,
  streamingId: null as string | null,
  lastAbandonedRunId: null as string | null,
  interruptedMessageId: null as string | null,
  continuingId: null as string | null,
  skipThinking: false,
  pendingVersions: null as string[] | null,
  pendingThinkingVersions: null as string[] | null,
  wsStatus: 'disconnected' as const,
  submissionConvId: null as string | null,
  activeTeamId: null as string | null,
  selectedAgentId: null as string | null,
};

beforeEach(() => {
  useChatStore.setState(initialState);
  vi.clearAllMocks();
  localStorage.clear();
  mockListKeys.mockResolvedValue([
    {
      id: 'key-1',
      is_default: true,
      is_active: true,
      models: ['deepseek-chat'],
    },
  ]);
  mockSubmitReq.mockResolvedValue({
    run_id: 'run-1',
    status: 'running',
    session_id: 'sess-1',
  });
  mockResumeRun.mockResolvedValue({
    run_id: 'run-2',
    status: 'running',
    session_id: 'sess-1',
  });
  localStorage.clear();
});

describe('editMessage', { tags: ['unit'] }, () => {
  it('updates content of message at given index', () => {
    const msg = makeMsg({ id: 'm1', content: 'old' });
    useChatStore.setState({ messages: [msg] });

    editMessage(0, 'new content');

    const updated = useChatStore.getState().messages[0];
    expect(updated.content).toBe('new content');
    expect(updated.id).toBe('m1');
  });

  it('handles out-of-bounds index by extending array', () => {
    const msg = makeMsg({ id: 'm1' });
    useChatStore.setState({ messages: [msg] });

    editMessage(5, 'new content');

    const messages = useChatStore.getState().messages;
    expect(messages).toHaveLength(6);
    expect(messages[5].content).toBe('new content');
    expect(messages[0].id).toBe('m1');
  });
});

describe('regenerateMessage', { tags: ['unit'] }, () => {
  it('does nothing if msgIndex < 1', async () => {
    const msg = makeMsg({ id: 'm2', content: 'hello' });
    useChatStore.setState({ messages: [msg], currentSessionId: 'sess-1' });

    await regenerateMessage(0);

    expect(mockSubmitReq).not.toHaveBeenCalled();
  });

  it('does nothing if user message at msgIndex-1 is missing', async () => {
    useChatStore.setState({ messages: [], currentSessionId: 'sess-1' });

    await regenerateMessage(1);

    expect(mockSubmitReq).not.toHaveBeenCalled();
  });

  it('disconnects current run, truncates messages, and re-submits', async () => {
    const { disconnectRun } = await import('../../api/websocket');
    const userMsg = makeMsg({ id: 'u1', role: 'user', content: 'original' });
    const agentMsg = makeMsg({ id: 'a1', role: 'agent', content: 'response' });
    useChatStore.setState({
      messages: [userMsg, agentMsg],
      currentSessionId: 'sess-1',
      currentRunId: 'old-run',
    });

    await regenerateMessage(1);

    expect(disconnectRun).toHaveBeenCalledWith('old-run');
    const state = useChatStore.getState();
    expect(state.messages).toHaveLength(1);
    // 用户消息 rebind 到新 run（版本链末跳）；userVersions 由加载时挂载，
    // 流式路径不写
    expect(state.messages[0].id).toBe('run-run-1-requirement');
    expect(state.messages[0].runId).toBe('run-1');
    expect(state.messages[0].versionRunIds).toEqual(['run-1']);
    expect(state.messages[0].userVersions).toBeUndefined();
    expect(state.pendingRegenerate).toMatchObject({
      userMsgId: 'u1',
      oldRunIds: [],
      requirement: 'original',
    });
    expect(mockSubmitReq).toHaveBeenCalledWith(
      'original',
      'sess-1',
      'key-1',
      'deepseek-chat',
      null,
    );
  });

  it('routes to the key whose models contain the UI-selected model (SiliconFlow case)', async () => {
    // Two active keys, neither default: an earlier DeepSeek key and a newer SiliconFlow key.
    mockListKeys.mockResolvedValue([
      {
        id: 'deepseek-key',
        is_default: false,
        is_active: true,
        models: ['deepseek-v4-flash'],
      },
      {
        id: 'siliconflow-key',
        is_default: false,
        is_active: true,
        models: ['Qwen/Qwen3-8B', 'deepseek-ai/DeepSeek-V4-Flash'],
      },
    ]);
    localStorage.setItem('ragbase-selected-model', 'Qwen/Qwen3-8B');

    const userMsg = makeMsg({ id: 'u1', role: 'user', content: 'original' });
    const agentMsg = makeMsg({ id: 'a1', role: 'agent', content: 'response' });
    useChatStore.setState({
      messages: [userMsg, agentMsg],
      currentSessionId: 'sess-1',
      currentRunId: 'old-run',
    });

    await regenerateMessage(1);

    expect(mockSubmitReq).toHaveBeenCalledWith(
      'original',
      'sess-1',
      'siliconflow-key',
      'Qwen/Qwen3-8B',
      null,
    );
  });

  it('passes parent_run_id from the user message parentRunId (sibling branch)', async () => {
    const userMsg = makeMsg({
      id: 'u1',
      role: 'user',
      content: 'original',
      parentRunId: 'run-2',
    });
    const agentMsg = makeMsg({ id: 'a1', role: 'agent', content: 'response' });
    useChatStore.setState({
      messages: [userMsg, agentMsg],
      currentSessionId: 'sess-1',
      currentRunId: 'old-run',
    });

    await regenerateMessage(1);

    expect(mockSubmitReq).toHaveBeenCalledWith(
      'original',
      'sess-1',
      'key-1',
      'deepseek-chat',
      'run-2',
    );
  });

  it('re-branches at the turn parent, not the turn itself (synthetic id ignored)', async () => {
    const userMsg = makeMsg({
      id: 'run-run-abc-requirement',
      role: 'user',
      content: 'original',
      parentRunId: 'run-1',
    });
    const agentMsg = makeMsg({ id: 'a1', role: 'agent', content: 'response' });
    useChatStore.setState({
      messages: [userMsg, agentMsg],
      currentSessionId: 'sess-1',
      currentRunId: 'old-run',
    });

    await regenerateMessage(1);

    expect(mockSubmitReq).toHaveBeenCalledWith(
      'original',
      'sess-1',
      'key-1',
      'deepseek-chat',
      'run-1',
    );
  });
});

describe('editAndRegenerate', { tags: ['unit'] }, () => {
  it('merges into the following agent answer and activates the new run', async () => {
    const userMsg = makeMsg({
      id: 'u1',
      role: 'user',
      content: 'old question',
    });
    const agentMsg = makeMsg({ id: 'a1', role: 'pm', content: 'old answer' });
    useChatStore.setState({
      messages: [userMsg, agentMsg],
      currentSessionId: 'sess-1',
      currentRunId: 'old-run',
    });

    const { editAndRegenerate } = await import('../chatActions');
    await editAndRegenerate('u1', 'new question');

    const s = useChatStore.getState();
    expect(s.editTargetId).toBe('a1');
    expect(s.activeRunId).toBe('run-1');
    const updatedUser = s.messages[0];
    expect(updatedUser.content).toBe('new question');
    // Edit history archived on the user message (version chain drives branch nav).
    expect(updatedUser.userVersions).toEqual(['old question', 'new question']);
    expect(updatedUser.currentUserVersion).toBe(1);
    // The old answer is NOT deleted — it stays as the merge target for the stream.
    // (User message id is rewritten to the synthetic run-{run_id}-requirement by
    // submitRequirement for edit routing.)
    expect(s.messages.map((m) => m.id)).toEqual([
      'run-run-1-requirement',
      'a1',
    ]);
    expect(mockSubmitReq).toHaveBeenCalledWith(
      'new question',
      'sess-1',
      'key-1',
      'deepseek-chat',
      null,
    );
  });

  it('regenerates even when the edited user message has no following agent answer', async () => {
    useChatStore.setState({
      messages: [makeMsg({ id: 'u1', role: 'user', content: 'solo' })],
      currentSessionId: 'sess-1',
    });

    const { editAndRegenerate } = await import('../chatActions');
    await editAndRegenerate('u1', 'edited solo');

    const s = useChatStore.getState();
    expect(s.editTargetId).toBeNull();
    expect(s.activeRunId).toBe('run-1');
    expect(s.messages[0].content).toBe('edited solo');
    expect(s.messages[0].userVersions).toEqual(['solo', 'edited solo']);
    expect(s.messages[0].currentUserVersion).toBe(1);
    expect(mockSubmitReq).toHaveBeenCalledWith(
      'edited solo',
      'sess-1',
      'key-1',
      'deepseek-chat',
      null,
    );
  });

  it('does nothing when content is unchanged', async () => {
    useChatStore.setState({
      messages: [makeMsg({ id: 'u1', role: 'user', content: 'same' })],
      currentSessionId: 'sess-1',
    });

    const { editAndRegenerate } = await import('../chatActions');
    await editAndRegenerate('u1', '  same  ');

    expect(mockSubmitReq).not.toHaveBeenCalled();
    expect(useChatStore.getState().messages[0].userVersions).toBeUndefined();
  });

  it('appends to the version chain on a second edit', async () => {
    // Version chain grows on each edit: [v1, v2] → [v1, v2, v3].
    useChatStore.setState({
      messages: [
        makeMsg({
          id: 'u1',
          role: 'user',
          content: 'v2 content',
          userVersions: ['v1 content', 'v2 content'],
        }),
      ],
      currentSessionId: 'sess-1',
    });

    const { editAndRegenerate } = await import('../chatActions');
    await editAndRegenerate('u1', 'v3 content');

    const msg = useChatStore.getState().messages[0];
    expect(msg.content).toBe('v3 content');
    expect(msg.userVersions).toEqual([
      'v1 content',
      'v2 content',
      'v3 content',
    ]);
    expect(msg.currentUserVersion).toBe(2);
  });

  it('uses parentRunId from the loaded message (not synthetic id parsing)', async () => {
    // Loaded user messages carry parent_run_id (buildPathTurns); edits branch a
    // sibling from it. Synthetic "run-{id}-requirement" parsing is gone.
    useChatStore.setState({
      messages: [
        makeMsg({
          id: 'run-abc123-requirement',
          role: 'user',
          content: 'old',
          parentRunId: 'parent-7',
        }),
      ],
      currentSessionId: 'sess-1',
    });

    const { editAndRegenerate } = await import('../chatActions');
    await editAndRegenerate('run-abc123-requirement', 'edited');

    expect(mockSubmitReq).toHaveBeenCalledWith(
      'edited',
      'sess-1',
      'key-1',
      'deepseek-chat',
      'parent-7',
    );
  });
});

describe('submitRequirement user-message binding', { tags: ['unit'] }, () => {
  it('rewrites the added user message id to run-{run_id}-requirement for edit routing', async () => {
    useChatStore.setState({
      messages: [makeMsg({ id: 'existing', role: 'agent', content: 'prev' })],
      currentSessionId: 'sess-1',
    });
    mockSubmitReq.mockResolvedValue({
      run_id: 'e69b278c-1234-4b6c-994c-f83084d5b4f3',
      status: 'running',
      session_id: 'sess-1',
    });

    const { submitRequirement } = await import('../chatActions');
    await submitRequirement('hello new session');

    const msgs = useChatStore.getState().messages;
    const last = msgs[msgs.length - 1];
    expect(last.role).toBe('user');
    expect(last.id).toBe(
      'run-e69b278c-1234-4b6c-994c-f83084d5b4f3-requirement',
    );
  });
});

describe('retry', { tags: ['unit'] }, () => {
  it('sets error if no user message found', async () => {
    useChatStore.setState({ messages: [], currentSessionId: 'sess-1' });

    await retry();

    const state = useChatStore.getState();
    expect(state.status).toBe('error');
    expect(state.error).toBe(
      '\u6ca1\u6709\u627e\u5230\u7528\u6237\u6d88\u606f\uff0c\u65e0\u6cd5\u91cd\u8bd5',
    );
  });

  it('re-submits the last user message', async () => {
    const { connectRun } = await import('../../api/websocket');
    const msg1 = makeMsg({ id: 'u1', role: 'user', content: 'question' });
    const msg2 = makeMsg({ id: 'a1', role: 'agent', content: 'answer' });
    const msg3 = makeMsg({ id: 'u2', role: 'user', content: 'follow-up' });
    useChatStore.setState({
      messages: [msg1, msg2, msg3],
      currentSessionId: 'sess-1',
      currentRunId: 'old-run',
    });

    await retry();

    const state = useChatStore.getState();
    expect(state.currentRunId).toBe('run-1');
    expect(state.status).toBe('running');
    expect(mockSubmitReq).toHaveBeenCalledWith('follow-up', 'sess-1');
    expect(connectRun).toHaveBeenCalled();
  });

  it('handles retry API failure', async () => {
    mockSubmitReq.mockRejectedValueOnce(new Error('API Error'));
    const msg1 = makeMsg({ id: 'u1', role: 'user', content: 'question' });
    const msg2 = makeMsg({ id: 'a1', role: 'agent', content: 'answer' });
    useChatStore.setState({
      messages: [msg1, msg2],
      currentSessionId: 'sess-1',
      currentRunId: 'old-run',
    });

    await retry();

    const state = useChatStore.getState();
    expect(state.status).toBe('error');
    expect(state.error).toBe('API Error');
  });
});

describe('continueGeneration', { tags: ['unit'] }, () => {
  it('does nothing if interruptedMessageId is null', async () => {
    useChatStore.setState({ interruptedMessageId: null });

    await continueGeneration();

    expect(mockResumeRun).not.toHaveBeenCalled();
  });

  it('clears interruptedMessageId if message not found in list', async () => {
    useChatStore.setState({
      interruptedMessageId: 'missing-id',
      messages: [],
    });

    await continueGeneration();

    expect(useChatStore.getState().interruptedMessageId).toBeNull();
    expect(mockResumeRun).not.toHaveBeenCalled();
  });

  it('resumes run with continuation for interrupted message', async () => {
    const { connectRun } = await import('../../api/websocket');
    const interrupted = makeMsg({
      id: 'int-1',
      role: 'agent',
      content: 'partial response',
      thinking: 'some thinking',
    });
    useChatStore.setState({
      interruptedMessageId: 'int-1',
      messages: [interrupted],
      currentSessionId: 'sess-1',
      currentRunId: 'pending-run',
    });

    await continueGeneration();

    expect(mockResumeRun).toHaveBeenCalledWith(
      'partial response',
      'sess-1',
      'some thinking',
      'deepseek-chat',
      undefined,
    );
    const state = useChatStore.getState();
    expect(state.currentRunId).toBe('run-2');
    expect(state.status).toBe('running');
    expect(connectRun).toHaveBeenCalled();
  });

  it('passes the original user question for seamless continuation', async () => {
    const userMsg = makeMsg({
      id: 'user-1',
      role: 'user',
      content: '原问题是什么？',
    });
    const interrupted = makeMsg({
      id: 'int-1b',
      role: 'agent',
      content: '半截回答',
      thinking: '思考',
    });
    useChatStore.setState({
      interruptedMessageId: 'int-1b',
      messages: [userMsg, interrupted],
      currentSessionId: 'sess-1',
    });

    await continueGeneration();

    expect(mockResumeRun).toHaveBeenCalledWith(
      '半截回答',
      'sess-1',
      '思考',
      'deepseek-chat',
      '原问题是什么？',
    );
  });

  it('aborts when interrupted message has neither content nor thinking', async () => {
    const interrupted = makeMsg({
      id: 'int-4',
      role: 'agent',
      content: '',
      thinking: '',
    });
    useChatStore.setState({
      interruptedMessageId: 'int-4',
      messages: [interrupted],
      currentSessionId: 'sess-1',
    });

    await continueGeneration();

    expect(mockResumeRun).not.toHaveBeenCalled();
    const state = useChatStore.getState();
    expect(state.interruptedMessageId).toBeNull();
    expect(state.error).toBe('没有可续写的内容，请重新生成');
  });

  it('resumes with thinking as material when content was interrupted mid-reasoning', async () => {
    const interrupted = makeMsg({
      id: 'int-5',
      role: 'agent',
      content: '',
      thinking: 'half-built reasoning chain',
    });
    useChatStore.setState({
      interruptedMessageId: 'int-5',
      messages: [interrupted],
      currentSessionId: 'sess-1',
    });

    await continueGeneration();

    expect(mockResumeRun).toHaveBeenCalledWith(
      '',
      'sess-1',
      'half-built reasoning chain',
      'deepseek-chat',
      undefined,
    );
    const state = useChatStore.getState();
    expect(state.currentRunId).toBe('run-2');
    expect(state.status).toBe('running');
  });

  it('does not archive versions into pending state (dead field in branch model)', async () => {
    // Branch model: continuation replaces the interrupted message; versions are
    // not carried into pendingVersions (field is a leftover, never consumed).
    const interrupted = makeMsg({
      id: 'int-2',
      role: 'agent',
      content: 'v2 content',
      thinking: undefined,
      versions: ['v1', 'v2'],
    } as Partial<ChatMessage> & { versions: string[] });
    useChatStore.setState({
      interruptedMessageId: 'int-2',
      messages: [interrupted],
      currentSessionId: 'sess-1',
    });

    await continueGeneration();

    const state = useChatStore.getState();
    expect(state.pendingVersions).toBeNull();
    expect(state.pendingThinkingVersions).toBeNull();
  });

  it('handles error during resume', async () => {
    mockResumeRun.mockRejectedValueOnce(new Error('Resume failed'));
    const interrupted = makeMsg({
      id: 'int-3',
      role: 'agent',
      content: 'partial',
    });
    useChatStore.setState({
      interruptedMessageId: 'int-3',
      messages: [interrupted],
      currentSessionId: 'sess-1',
    });

    await continueGeneration();

    const state = useChatStore.getState();
    expect(state.status).toBe('error');
    expect(state.error).toBe('Resume failed');
  });

  it('handles non-Error error during resume', async () => {
    mockResumeRun.mockRejectedValueOnce('string error');
    const interrupted = makeMsg({
      id: 'int-4',
      role: 'agent',
      content: 'partial',
    });
    useChatStore.setState({
      interruptedMessageId: 'int-4',
      messages: [interrupted],
      currentSessionId: 'sess-1',
    });

    await continueGeneration();

    expect(useChatStore.getState().error).toBe('string error');
  });
});
