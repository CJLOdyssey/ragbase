import {
  handleResultEvent,
  handleTeamResultEvent,
  handleThinkingDone,
  handleThinkingDoneEvent,
  handleThumbsEvent,
} from '../resultHandler';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../utils/logger', () => ({
  default: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
}));

vi.mock('./uid', () => ({ uid: vi.fn(() => 'test-uid') }));

function makeMsg(id: string, overrides: Record<string, unknown> = {}) {
  return {
    id,
    role: 'agent',
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
    messages: [makeMsg('msg-1')],
    status: 'streaming',
    currentRole: 'Agent',
    wsStatus: 'connected',
    skipThinking: false,
    continuingId: null,
    pendingVersions: null,
    pendingThinkingVersions: null,
    ...overrides,
  };
}

describe('handleThinkingDone', { tags: ['unit'] }, () => {
  it('returns empty object when no continuingId', () => {
    const s = makeState({ continuingId: null });
    const result = handleThinkingDone(s as never, {
      type: 'thinking_done',
      thinking: 'final thoughts',
    });
    expect(result).toEqual({});
  });

  it('creates new message replacing continuing message', () => {
    const s = makeState({
      continuingId: 'msg-1',
      messages: [makeMsg('msg-1')],
    });

    const result = handleThinkingDone(s as never, {
      type: 'thinking_done',
      thinking: 'final thoughts',
      agent_name: 'Bot',
    });

    expect(result.streamingId).toBeDefined();
    expect(result.continuingId).toBeNull();
    expect(result.messages).toBeDefined();
    expect(result.messages![0].thinking).toBe('final thoughts');
  });

  it('handles continuing message not found in messages', () => {
    const s = makeState({
      continuingId: 'nonexistent',
      messages: [makeMsg('other')],
    });

    const result = handleThinkingDone(s as never, {
      type: 'thinking_done',
      thinking: 'thoughts',
    });

    expect(result.messages).toBeDefined();
    expect(result.messages![0].agent_name).toBe('Agent');
  });

  it('preserves versions when pendingVersions present', () => {
    const s = makeState({
      continuingId: 'msg-1',
      pendingVersions: ['v1', 'v2'],
      pendingThinkingVersions: ['tv1'],
      messages: [
        makeMsg('msg-1', { content: 'old content', thinking: 'old think' }),
      ],
    });

    const result = handleThinkingDone(s as never, {
      type: 'thinking_done',
      thinking: 'new think',
    });

    expect(result.pendingVersions).toBeNull();
    expect(result.pendingThinkingVersions).toBeNull();
    expect(result.messages![0].versions).toBeDefined();
    expect(
      result.messages![0].versions![result.messages![0].versions!.length - 1],
    ).toBe('old content');
  });
});

describe('handleThinkingDoneEvent', { tags: ['unit'] }, () => {
  it('marks thinkingDone on streaming message', () => {
    const s = makeState({
      streamingId: 'msg-1',
      messages: [makeMsg('msg-1')],
    });

    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    handleThinkingDoneEvent(set as never, { type: 'thinking_done' });

    const result = set.mock.results[0].value as {
      messages: Array<{ thinkingDone?: boolean }>;
    };
    expect(result.messages![0].thinkingDone).toBe(true);
  });

  it('delegates to handleThinkingDone when no streamingId', () => {
    const s = makeState({
      streamingId: null,
      continuingId: 'msg-1',
      messages: [makeMsg('msg-1')],
    });

    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    handleThinkingDoneEvent(set as never, {
      type: 'thinking_done',
      thinking: 'done',
    });

    const result = set.mock.results[0].value as { streamingId: string | null };
    expect(result.streamingId).toBeDefined();
  });
});

describe('handleResultEvent', { tags: ['unit'] }, () => {
  it('sets status to idle and clears streamingId', () => {
    const s = makeState({
      streamingId: 'msg-1',
      messages: [makeMsg('msg-1', { thinking: 't', content: 'old' })],
    });
    const get = vi.fn(() => s);
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    const activeStreams = new Set<string>();

    handleResultEvent(set as never, get, activeStreams, {
      type: 'result',
      code: 'result code',
    });

    const result = set.mock.results[0].value as {
      status: string;
      streamingId: null;
      result: { code: string };
    };
    expect(result.status).toBe('idle');
    expect(result.streamingId).toBeNull();
  });

  it('updates content with code when streamingId matches', () => {
    const s = makeState({
      streamingId: 'msg-1',
      messages: [makeMsg('msg-1', { thinking: 't', content: 'old' })],
    });
    const get = vi.fn(() => s);
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    const activeStreams = new Set<string>(['run-1']);

    handleResultEvent(set as never, get, activeStreams, {
      type: 'result',
      code: 'final code',
      run_id: 'run-1',
    });

    const result = set.mock.results[0].value as {
      messages: Array<{ content: string; thinkingDone: boolean }>;
    };
    expect(result.messages![0].content).toBe('final code');
    expect(result.messages![0].thinkingDone).toBe(true);
  });

  it('handles result without code', () => {
    const s = makeState({
      streamingId: 'msg-1',
      messages: [makeMsg('msg-1', { thinking: 't', content: 'old' })],
    });
    const get = vi.fn(() => s);
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    const activeStreams = new Set<string>();

    handleResultEvent(set as never, get, activeStreams, {
      type: 'result',
      code: '',
    });

    const result = set.mock.results[0].value as {
      messages: Array<{ content: string }>;
    };
    expect(result.messages![0].content).toBe('old');
  });

  it('handles empty thinking becoming undefined on result', () => {
    const s = makeState({
      streamingId: 'msg-1',
      messages: [makeMsg('msg-1', { thinking: '', content: 'old' })],
    });
    const get = vi.fn(() => s);
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    const activeStreams = new Set<string>();

    handleResultEvent(set as never, get, activeStreams, {
      type: 'result',
      code: '',
    });

    const result = set.mock.results[0].value as {
      messages: Array<{ thinking: string | undefined; thinkingDone: boolean }>;
    };
    expect(result.messages![0].thinking).toBeUndefined();
  });
});

describe('handleTeamResultEvent', { tags: ['unit'] }, () => {
  it('sets status to idle and marks thinkingDone', () => {
    const s = makeState({
      streamingId: 'msg-1',
      messages: [makeMsg('msg-1')],
    });
    const get = vi.fn(() => s);
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    const activeStreams = new Set<string>(['run-1']);

    handleTeamResultEvent(set as never, get, activeStreams, {
      type: 'team_result',
    });

    const result = set.mock.results[0].value as {
      status: string;
      streamingId: null;
      messages: Array<{ thinkingDone: boolean }>;
    };
    expect(result.status).toBe('idle');
    expect(result.streamingId).toBeNull();
    expect(result.messages![0].thinkingDone).toBe(true);
  });

  it('handles team_result without streamingId', () => {
    const s = makeState({ streamingId: null, messages: [makeMsg('msg-1')] });
    const get = vi.fn(() => s);
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    const activeStreams = new Set<string>();

    handleTeamResultEvent(set as never, get, activeStreams, {
      type: 'team_result',
    });

    const result = set.mock.results[0].value as {
      status: string;
      streamingId: null;
    };
    expect(result.status).toBe('idle');
    expect(result.streamingId).toBeNull();
  });

  it('replaces streamed content with composed per-node artifact display', () => {
    const s = makeState({
      streamingId: 'msg-1',
      messages: [makeMsg('msg-1', { content: 'raw concatenated nodes' })],
    });
    const get = vi.fn(() => s);
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    const activeStreams = new Set<string>(['run-1']);

    const display = '## pm\n\n需求文档\n\n---\n\n## reviewer\n\n审查通过';
    handleTeamResultEvent(set as never, get, activeStreams, {
      type: 'team_result',
      artifacts: { pm: '需求文档', reviewer: '审查通过' },
      display,
    });

    const result = set.mock.results[0].value as {
      status: string;
      messages: Array<{ content: string; thinkingDone: boolean }>;
    };
    expect(result.status).toBe('idle');
    expect(result.streamingId).toBeNull();
    expect(result.messages![0].thinkingDone).toBe(true);
    expect(result.messages![0].content).toBe(display);
  });

  it('keeps existing content when team_result has no display', () => {
    const s = makeState({
      streamingId: 'msg-1',
      messages: [makeMsg('msg-1', { content: 'old' })],
    });
    const get = vi.fn(() => s);
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));
    const activeStreams = new Set<string>(['run-1']);

    handleTeamResultEvent(set as never, get, activeStreams, {
      type: 'team_result',
      artifacts: {},
    });

    const result = set.mock.results[0].value as {
      messages: Array<{ content: string }>;
    };
    expect(result.messages![0].content).toBe('old');
    expect(result.messages![0].thinkingDone).toBe(true);
  });
});

describe('handleThumbsEvent', { tags: ['unit'] }, () => {
  it('sets thumbs value on matching message', () => {
    const s = makeState({
      messages: [makeMsg('msg-1'), makeMsg('msg-2')],
    });
    const set = vi.fn((fn: (state: typeof s) => Partial<typeof s>) => fn(s));

    handleThumbsEvent(set as never, {
      type: 'thumbs',
      msgId: 'msg-1',
      value: 'up',
    });

    const updateFn = set.mock.calls[0][0];
    const result = updateFn(s) as { messages: Array<{ thumbs?: string }> };
    expect(result.messages![0].thumbs).toBe('up');
    expect(result.messages![1].thumbs).toBeUndefined();
  });
});
