import {
  handleBalanceWarningEvent,
  handleErrorEvent,
  handleInfoEvent,
  handleMessageEvent,
  handleOpenUrlEvent,
} from '../messageHandler';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../utils/logger', () => ({
  default: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
}));

vi.mock('./uid', () => ({ uid: vi.fn(() => 'test-uid') }));

function makeState(overrides: Record<string, unknown> = {}) {
  return {
    currentRunId: 'run-1',
    streamingId: 'msg-1',
    messages: [
      {
        id: 'msg-1',
        role: 'agent',
        content: 'Hello',
        thinking: 'thinking...',
        agent_name: 'Agent',
        round_number: 0,
        created_at: new Date().toISOString(),
      },
    ],
    status: 'running',
    currentRole: 'Agent',
    wsStatus: 'connected',
    skipThinking: false,
    continuingId: null,
    ...overrides,
  };
}

describe('handleMessageEvent', { tags: ['unit'] }, () => {
  it('updates content and thinking when streamingId matches', () => {
    const set = vi.fn((fn: (s: ReturnType<typeof makeState>) => unknown) => {
      const s = makeState();
      const result = fn(s);
      return result;
    });

    handleMessageEvent(set as never, {
      type: 'message',
      content: 'Updated',
      thinking: 'new thinking',
      role: 'agent',
    });

    const updateFn = set.mock.calls[0][0];
    const result = updateFn(makeState());
    expect(result.messages[0].content).toBe('Updated');
    expect(result.messages[0].thinking).toBe('new thinking');
  });

  it('creates new message when no streamingId', () => {
    const set = vi.fn((fn: (s: ReturnType<typeof makeState>) => unknown) =>
      fn(makeState({ streamingId: null })),
    );

    handleMessageEvent(set as never, {
      type: 'message',
      content: 'New msg',
      thinking: 'think',
      role: 'assistant',
      agent_name: 'Bot',
      round_number: 1,
    });

    const result = set.mock.results[0].value as {
      messages: Array<{ content: string }>;
    };
    expect(result.messages).toHaveLength(2);
    expect(result.messages[1].content).toBe('New msg');
  });

  it('ignores message event when run finished (status idle — reconnect replay)', () => {
    const set = vi.fn((fn: (s: ReturnType<typeof makeState>) => unknown) =>
      fn(makeState({ streamingId: null, status: 'idle' })),
    );

    handleMessageEvent(set as never, {
      type: 'message',
      content: 'Replayed',
      thinking: '',
      role: 'agent',
      agent_name: 'Agent',
    });

    const result = set.mock.results[0].value;
    expect(result).toEqual({});
  });
});

describe('handleInfoEvent', { tags: ['unit'] }, () => {
  it('appends info to streaming message (content 优先)', () => {
    const set = vi.fn((fn: (s: ReturnType<typeof makeState>) => unknown) =>
      fn(makeState()),
    );

    handleInfoEvent(set as never, {
      type: 'info',
      content: 'Fetching data...',
      data: 'extra',
    });

    const result = set.mock.results[0].value as {
      messages: Array<{ content: string }>;
    };
    expect(result.messages[0].content).toContain('[Fetching data...]');
  });

  it('content 缺失时回退到 data，绝不追加 undefined', () => {
    const set = vi.fn((fn: (s: ReturnType<typeof makeState>) => unknown) =>
      fn(makeState()),
    );

    handleInfoEvent(set as never, {
      type: 'info',
      data: 'extra',
    });

    const result = set.mock.results[0].value as {
      messages: Array<{ content: string }>;
    };
    expect(result.messages[0].content).toContain('[extra]');
    expect(result.messages[0].content).not.toContain('undefined');
  });

  it('returns empty state when no streamingId', () => {
    const set = vi.fn((fn: (s: ReturnType<typeof makeState>) => unknown) =>
      fn(makeState({ streamingId: null })),
    );

    handleInfoEvent(set as never, { type: 'info', content: 'note' });

    const result = set.mock.results[0].value;
    expect(result).toEqual({});
  });

  it('uses data string when content is not set', () => {
    const set = vi.fn((fn: (s: ReturnType<typeof makeState>) => unknown) =>
      fn(makeState()),
    );

    handleInfoEvent(set as never, { type: 'info', data: 'raw-data' });

    const result = set.mock.results[0].value as {
      messages: Array<{ content: string }>;
    };
    expect(result.messages[0].content).toContain('[raw-data]');
  });
});

describe('handleErrorEvent', { tags: ['unit'] }, () => {
  it('sets status to error with message', () => {
    const set = vi.fn((fn: (s: ReturnType<typeof makeState>) => unknown) =>
      fn(makeState()),
    );

    handleErrorEvent(set as never, {
      type: 'error',
      content: 'Something broke',
    });

    const result = set.mock.results[0].value as {
      status: string;
      error: string;
    };
    expect(result.status).toBe('error');
    expect(result.error).toBe('Something broke');
  });

  it('clears continuing/edit pending state so the UI never sticks', () => {
    const set = vi.fn((fn: (s: ReturnType<typeof makeState>) => unknown) =>
      fn(makeState({ continuingId: 'msg-1', editTargetId: 'msg-1' })),
    );

    handleErrorEvent(set as never, {
      type: 'error',
      content: 'boom',
    });

    const result = set.mock.results[0].value as Record<string, unknown>;
    expect(result.continuingId).toBeNull();
    expect(result.editTargetId).toBeNull();
    expect(result.pendingVersions).toBeNull();
    expect(result.pendingThinkingVersions).toBeNull();
    expect(result.streamingId).toBeNull();
  });

  it('defaults error message when content is missing', () => {
    const set = vi.fn((fn: (s: ReturnType<typeof makeState>) => unknown) =>
      fn(makeState()),
    );

    handleErrorEvent(set as never, { type: 'error' });

    const result = set.mock.results[0].value as { error: string };
    expect(result.error).toBe('Unknown error');
  });
});

describe('handleBalanceWarningEvent', { tags: ['unit'] }, () => {
  it('sets status to error with balance warning', () => {
    const set = vi.fn((fn: (s: ReturnType<typeof makeState>) => unknown) =>
      fn(makeState()),
    );

    handleBalanceWarningEvent(set as never, {
      type: 'balance_warning',
      content: 'Low balance',
    });

    const result = set.mock.results[0].value as {
      status: string;
      error: string;
    };
    expect(result.status).toBe('error');
    expect(result.error).toBe('Low balance');
  });

  it('defaults to Chinese message when no content', () => {
    const set = vi.fn((fn: (s: ReturnType<typeof makeState>) => unknown) =>
      fn(makeState()),
    );

    handleBalanceWarningEvent(set as never, { type: 'balance_warning' });

    const result = set.mock.results[0].value as { error: string };
    expect(result.error).toBe('模型余额不足');
  });
});

describe('handleOpenUrlEvent', { tags: ['unit'] }, () => {
  it('dispatches browser-open-url event with the URL', () => {
    const dispatched: string[] = [];
    const listener = (e: Event) =>
      dispatched.push((e as CustomEvent<string>).detail);
    window.addEventListener('browser-open-url', listener);

    handleOpenUrlEvent({ type: 'open_url', url: 'https://example.com' });

    expect(dispatched).toEqual(['https://example.com']);
    window.removeEventListener('browser-open-url', listener);
  });

  it('does nothing when url is empty', () => {
    const dispatched: string[] = [];
    const listener = (e: Event) =>
      dispatched.push((e as CustomEvent<string>).detail);
    window.addEventListener('browser-open-url', listener);

    handleOpenUrlEvent({ type: 'open_url' });

    expect(dispatched).toEqual([]);
    window.removeEventListener('browser-open-url', listener);
  });
});
