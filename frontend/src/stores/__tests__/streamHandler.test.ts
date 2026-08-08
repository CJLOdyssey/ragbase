import {
  handleStreamEvent,
  handleStreamStart,
  handleThinkingStreamEvent,
  handleThinkingStreamNew,
} from '../streamHandler';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../utils/logger', () => ({
  default: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
}));

vi.mock('./uid', () => ({ uid: vi.fn(() => 'uid-fixed') }));

function makeMsg(id: string, overrides: Record<string, unknown> = {}) {
  return {
    id,
    role: 'agent' as const,
    content: 'content' + id,
    thinking: 'think' + id,
    agent_name: 'Agent',
    round_number: 0,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

function makeState(overrides: Record<string, unknown> = {}) {
  return {
    currentRunId: 'run-1',
    streamingId: null,
    messages: [],
    status: 'streaming',
    currentRole: null,
    wsStatus: 'connected',
    skipThinking: false,
    continuingId: null,
    pendingVersions: null,
    pendingThinkingVersions: null,
    ...overrides,
  };
}

describe('handleStreamStart', { tags: ['unit'] }, () => {
  it('creates new message with chunk when no continuingId', () => {
    const s = makeState();
    const msg = { type: 'stream' as const, content: '', agent_name: 'Bot' };
    const result = handleStreamStart(s as never, msg, 'hello');

    expect(result.streamingId).toBeDefined();
    expect(result.messages![0].content).toBe('hello');
    expect(result.messages![0].agent_name).toBe('Bot');
    expect(result.currentRole).toBe('Bot');
  });

  it('defaults agent name to Agent', () => {
    const s = makeState();
    const result = handleStreamStart(s as never, { type: 'stream' }, 'hi');

    expect(result.messages![0].agent_name).toBe('Agent');
  });

  it('replaces continuing message when continuingId present', () => {
    const s = makeState({
      continuingId: 'msg-1',
      messages: [
        makeMsg('msg-1', { content: 'interrupted', thinking: 'was thinking' }),
      ],
    });

    const result = handleStreamStart(
      s as never,
      { type: 'stream', agent_name: 'Bot' },
      ' continues',
    );

    expect(result.continuingId).toBeNull();
    expect(result.messages![0].content).toBe('interrupted continues');
    expect(result.messages![0].agent_name).toBe('Agent');
  });

  it('clears pendingVersions during continuation (no archival in branch model)', () => {
    // Branch model (edit=新分支 run, ee48c1d): pendingVersions is a dead field —
    // the interrupted message is REPLACED by the continuation stream, never
    // archived into versions.
    const s = makeState({
      continuingId: 'msg-1',
      pendingVersions: ['v1'],
      pendingThinkingVersions: ['t1'],
      messages: [makeMsg('msg-1', { content: 'old', thinking: 'old-think' })],
    });

    const result = handleStreamStart(s as never, { type: 'stream' }, ' new');

    expect(result.pendingVersions).toBeNull();
    expect(result.messages![0].versions).toBeUndefined();
    expect(result.messages![0].content).toBe('old new');
  });

  it('clears pendingVersions for new stream (no continuingId)', () => {
    const s = makeState({
      pendingVersions: ['v0'],
      pendingThinkingVersions: ['t0'],
    });

    const result = handleStreamStart(s as never, { type: 'stream' }, 'first');

    expect(result.pendingVersions).toBeNull();
    expect(result.messages![0].versions).toBeUndefined();
    expect(result.messages![0].content).toBe('first');
  });

  it('merges edit-regenerate answer into the target message (keeps other messages)', () => {
    const s = makeState({
      editTargetId: 'a1',
      messages: [
        makeMsg('u1', { role: 'user', content: 'new question' }),
        makeMsg('a1', { content: 'old answer', thinking: 'old think' }),
        makeMsg('a2', { content: 'later message' }),
      ],
    });

    const result = handleStreamStart(
      s as never,
      { type: 'stream', agent_name: 'Bot' },
      ' fresh',
    );

    expect(result.editTargetId).toBeNull();
    // Edit = new branch run: the target message is remapped to the new run's
    // message and the stream starts FRESH — old answer is NOT archived as a
    // version (branch navigation replaces it, DB keeps it).
    expect(result.messages![1].versions).toBeUndefined();
    expect(result.messages![1].content).toBe(' fresh');
    expect(result.messages![1].thinking).toBe('');
    expect(result.messages![1].currentVersion).toBeUndefined();
    // Other messages preserved — nothing deleted.
    expect(result.messages!.map((m) => m.id)).toEqual([
      'u1',
      result.messages![1].id,
      'a2',
    ]);
  });
});

describe('handleStreamEvent', { tags: ['unit'] }, () => {
  it('appends chunk to existing streaming message', () => {
    const s = makeState({
      streamingId: 'msg-1',
      currentRunId: 'run-1',
      messages: [makeMsg('msg-1', { content: 'Hello' })],
    });
    const get = vi.fn(() => s);
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    const activeStreams = new Set<string>(['run-1']);

    handleStreamEvent(set as never, get, activeStreams, {
      type: 'stream',
      content: ' world',
    } as never);

    const updateFn = set.mock.calls[0][0] as (
      state: typeof s,
    ) => Partial<typeof s>;
    const result = updateFn(s) as { messages: Array<{ content: string }> };
    expect(result.messages![0].content).toBe('Hello world');
  });

  it('returns early when chunk is empty', () => {
    const s = makeState({ streamingId: 'msg-1' });
    const get = vi.fn(() => s);
    const set = vi.fn();
    const activeStreams = new Set<string>();

    handleStreamEvent(set as never, get, activeStreams, {
      type: 'stream',
      content: '',
    } as never);

    expect(set).not.toHaveBeenCalled();
  });

  it('starts new stream when not active', () => {
    const s = makeState({
      currentRunId: 'run-1',
      messages: [],
    });
    const get = vi.fn(() => s);
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    const activeStreams = new Set<string>();

    handleStreamEvent(set as never, get, activeStreams, {
      type: 'stream',
      content: 'hi',
    } as never);

    expect(activeStreams.has('run-1')).toBe(true);

    const updateFn = set.mock.calls[0][0] as (
      state: typeof s,
    ) => Partial<typeof s>;
    const result = updateFn(s) as { messages: Array<{ content: string }> };
    expect(result.messages![0].content).toBe('hi');
  });

  it('starts a NEW message when run id is stale but streamingId is cleared', () => {
    // A leftover run id (result event lost / state reset) must not swallow the
    // first chunk of a stream; only treat it as continuation while streaming.
    const s = makeState({ streamingId: null, currentRunId: 'run-1' });
    const get = vi.fn(() => s);
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    const activeStreams = new Set<string>(['run-1']);

    handleStreamEvent(set as never, get, activeStreams, {
      type: 'stream',
      content: 'x',
    } as never);

    const updateFn = set.mock.calls[0][0] as (
      state: typeof s,
    ) => Partial<typeof s>;
    const result = updateFn(s) as { messages: Array<{ content: string }> };
    expect(result.messages![0].content).toBe('x');
  });
});

describe('handleThinkingStreamNew', { tags: ['unit'] }, () => {
  it('creates new message with thinking chunk', () => {
    const s = makeState();
    const result = handleThinkingStreamNew(
      s as never,
      { type: 'thinking_stream', agent_name: 'Bot' },
      'think content',
    );

    expect(result.messages![0].thinking).toBe('think content');
    expect(result.messages![0].content).toBe('');
    expect(result.currentRole).toBe('Bot');
  });

  it('replaces continuing message with accumulated thinking', () => {
    const s = makeState({
      continuingId: 'msg-1',
      messages: [makeMsg('msg-1', { thinking: 'old-think' })],
    });

    const result = handleThinkingStreamNew(
      s as never,
      { type: 'thinking_stream' },
      ' more',
    );

    expect(result.continuingId).toBeNull();
    expect(result.messages![0].thinking).toBe('old-think more');
  });

  it('clears pendingVersions during new thinking stream (no archival)', () => {
    const s = makeState({
      pendingVersions: ['v0'],
      pendingThinkingVersions: ['t0'],
    });

    const result = handleThinkingStreamNew(
      s as never,
      { type: 'thinking_stream' },
      'new-think',
    );

    expect(result.pendingVersions).toBeNull();
    expect(result.messages![0].versions).toBeUndefined();
    expect(result.messages![0].thinkingVersions).toBeUndefined();
    expect(result.messages![0].thinking).toBe('new-think');
  });

  it('merges edit-regenerate thinking into the target message (keeps other messages)', () => {
    const s = makeState({
      editTargetId: 'a1',
      messages: [
        makeMsg('u1', { role: 'user', content: 'new question' }),
        makeMsg('a1', { content: 'old answer', thinking: 'old think' }),
        makeMsg('a2', { content: 'later' }),
      ],
    });

    const result = handleThinkingStreamNew(
      s as never,
      { type: 'thinking_stream' },
      ' new think',
    );

    expect(result.editTargetId).toBeNull();
    // New thinking starts fresh; the old message is NOT archived (branch model).
    expect(result.messages![1].thinking).toBe(' new think');
    expect(result.messages![1].versions).toBeUndefined();
    expect(result.messages![1].thinkingVersions).toBeUndefined();
    expect(result.messages![1].content).toBe('');
    expect(result.messages!.map((m) => m.id)).toEqual([
      'u1',
      result.messages![1].id,
      'a2',
    ]);
  });
});

describe('handleThinkingStreamEvent', { tags: ['unit'] }, () => {
  it('appends to thinking on active stream', () => {
    const s = makeState({
      streamingId: 'msg-1',
      currentRunId: 'run-1',
      messages: [makeMsg('msg-1', { thinking: 'existing' })],
    });
    const get = vi.fn(() => s);
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    const activeStreams = new Set<string>(['run-1']);

    handleThinkingStreamEvent(set as never, get, activeStreams, {
      type: 'thinking_stream',
      content: ' more',
    } as never);

    const updateFn = set.mock.calls[0][0] as (
      state: typeof s,
    ) => Partial<typeof s>;
    const result = updateFn(s) as { messages: Array<{ thinking: string }> };
    expect(result.messages![0].thinking).toBe('existing more');
  });

  it('returns early when chunk is empty', () => {
    const s = makeState({ streamingId: 'msg-1' });
    const get = vi.fn(() => s);
    const set = vi.fn();
    const activeStreams = new Set<string>();

    handleThinkingStreamEvent(set as never, get, activeStreams, {
      type: 'thinking_stream',
      content: '',
    } as never);

    expect(set).not.toHaveBeenCalled();
  });

  it('starts new thinking stream when not active', () => {
    const s = makeState({
      currentRunId: 'run-1',
      streamingId: null,
      messages: [],
    });
    const get = vi.fn(() => s);
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    const activeStreams = new Set<string>();

    handleThinkingStreamEvent(set as never, get, activeStreams, {
      type: 'thinking_stream',
      content: 'think',
    } as never);

    expect(activeStreams.has('run-1')).toBe(true);
  });

  it('appends to thinking when active stream has existing streamingId', () => {
    const s = makeState({
      streamingId: 'msg-1',
      currentRunId: 'run-1',
      messages: [makeMsg('msg-1', { thinking: null })],
    });
    const get = vi.fn(() => s);
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    const activeStreams = new Set<string>(['run-1']);

    handleThinkingStreamEvent(set as never, get, activeStreams, {
      type: 'thinking_stream',
      content: 'new',
    } as never);

    const updateFn = set.mock.calls[0][0] as (
      state: typeof s,
    ) => Partial<typeof s>;
    const result = updateFn(s) as { messages: Array<{ thinking: string }> };
    expect(result.messages![0].thinking).toBe('new');
  });

  it('handles streamingId but not active (non-active update path)', () => {
    const s = makeState({
      streamingId: 'msg-1',
      currentRunId: 'run-1',
      messages: [makeMsg('msg-1', { thinking: 'old' })],
    });
    const get = vi.fn(() => s);
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    const activeStreams = new Set<string>(); // not active

    handleThinkingStreamEvent(set as never, get, activeStreams, {
      type: 'thinking_stream',
      content: 'chunk',
    } as never);

    expect(activeStreams.has('run-1')).toBe(true);
    const updateFn = set.mock.calls[0][0] as (
      state: typeof s,
    ) => Partial<typeof s>;
    const result = updateFn(s) as { messages: Array<{ thinking: string }> };
    expect(result.messages![0].thinking).toBe('oldchunk');
  });
});
