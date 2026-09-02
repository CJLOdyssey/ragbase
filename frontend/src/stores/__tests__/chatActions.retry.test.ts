// NOTE: vi.mock is hoisted above ALL imports — factories must not reference
// top-level bindings directly; async factories re-import the shared helpers.
import { continueGeneration, retry } from '../chatActions';
import { useChatStore } from '../chatStore';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ChatMessage } from '../../types';
import {
  makeMsg,
  mockListKeys,
  mockResumeRun,
  mockSubmitReq,
  resetMockDefaults,
} from './helpers/chatActionsTestUtils';

vi.mock('../../api/websocket', () => ({
  connectRun: vi.fn(() => vi.fn()),
  disconnectRun: vi.fn(),
}));

vi.mock('../../api/client', async () => {
  const h = await import('./helpers/chatActionsTestUtils');
  return {
    submitRequirement: h.mockSubmitReq,
    resumeRun: h.mockResumeRun,
    listKeys: h.mockListKeys,
    listAgents: vi.fn().mockResolvedValue([]),
  };
});

vi.mock('../chatStreaming', () => ({
  createStreamHandler: vi.fn(() => vi.fn()),
}));

beforeEach(async () => {
  await resetMockDefaults();
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
    // retry 走 store 完整流程（submitRequirement）：session 复用 + 消息绑定，
    // 不会因 currentSessionId 缺失而让后端新建会话。
    expect(mockSubmitReq).toHaveBeenCalledWith(
      'follow-up',
      'sess-1',
      'key-1',
      'deepseek-chat',
      null, // parent_run_id（根分支）
      undefined, // attachment_ids
      undefined, // prompt_id
    );
    expect(connectRun).toHaveBeenCalled();
  });

  it('routes retry to the key owning the UI-selected model (SiliconFlow case)', async () => {
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
        models: ['Qwen/Qwen3-8B', 'THUDM/GLM-Z1-9B-0414'],
      },
    ]);
    localStorage.setItem('ragbase-selected-model', 'THUDM/GLM-Z1-9B-0414');
    const msg1 = makeMsg({ id: 'u1', role: 'user', content: 'question' });
    const msg2 = makeMsg({ id: 'a1', role: 'agent', content: 'answer' });
    useChatStore.setState({
      messages: [msg1, msg2],
      currentSessionId: 'sess-1',
      currentRunId: 'old-run',
    });

    await retry();

    expect(mockSubmitReq).toHaveBeenCalledWith(
      'question',
      'sess-1',
      'siliconflow-key',
      'THUDM/GLM-Z1-9B-0414',
      null,
      undefined,
      undefined, // prompt_id
    );
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
      content: '\u539f\u95ee\u9898\u662f\u4ec0\u4e48\uff1f',
    });
    const interrupted = makeMsg({
      id: 'int-1b',
      role: 'agent',
      content: '\u534a\u622a\u56de\u7b54',
      thinking: '\u601d\u8003',
    });
    useChatStore.setState({
      interruptedMessageId: 'int-1b',
      messages: [userMsg, interrupted],
      currentSessionId: 'sess-1',
    });

    await continueGeneration();

    expect(mockResumeRun).toHaveBeenCalledWith(
      '\u534a\u622a\u56de\u7b54',
      'sess-1',
      '\u601d\u8003',
      'deepseek-chat',
      '\u539f\u95ee\u9898\u662f\u4ec0\u4e48\uff1f',
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
    expect(state.error).toBe(
      '\u6ca1\u6709\u53ef\u7eed\u5199\u7684\u5185\u5bb9\uff0c\u8bf7\u91cd\u65b0\u751f\u6210',
    );
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
