import {
  handleThinkingStreamEvent,
  handleThinkingStreamNew,
} from '../streamHandler';
import { describe, expect, it, vi } from 'vitest';
import { makeMsg, makeState } from './helpers/streamHandlerTestUtils';

vi.mock('../utils/logger', () => ({
  default: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
}));

vi.mock('./uid', () => ({ uid: vi.fn(() => 'uid-fixed') }));

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
