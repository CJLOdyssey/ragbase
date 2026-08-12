// NOTE: vi.mock is hoisted above ALL imports — factories must not reference
// top-level bindings directly; async factories re-import the shared helpers.
import { editMessage, regenerateMessage } from '../chatActions';
import { useChatStore } from '../chatStore';
import { beforeEach, describe, expect, it, vi } from 'vitest';
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
      undefined,
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
      undefined,
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
      undefined,
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
      undefined,
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
      undefined,
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
      undefined,
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
      undefined,
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
