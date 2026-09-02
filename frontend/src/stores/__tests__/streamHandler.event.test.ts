import { handleStreamEvent } from '../streamHandler';
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

  it('ignores stream event after run finished (status idle — reconnect replay)', () => {
    const s = makeState({
      status: 'idle',
      streamingId: null,
      currentRunId: 'run-1',
    });
    const get = vi.fn(() => s);
    const set = vi.fn();
    const activeStreams = new Set<string>();

    handleStreamEvent(set as never, get, activeStreams, {
      type: 'stream',
      content: 'replay',
    } as never);

    expect(set).not.toHaveBeenCalled();
  });
});
