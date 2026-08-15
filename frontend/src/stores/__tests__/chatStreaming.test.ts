import { createStreamHandler } from '../chatStreaming';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../utils/logger', () => ({
  default: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
}));

vi.mock('./uid', () => ({ uid: vi.fn(() => 'test-uid') }));

describe('chatStreaming', { tags: ['unit'] }, () => {
  function makeBasicState() {
    return {
      currentRunId: 'run-1',
      streamingId: 'stream-1',
      messages: [
        {
          id: 'stream-1',
          role: 'agent' as const,
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
      pendingVersions: null,
      pendingThinkingVersions: null,
      currentSessionId: 'sess-1',
    };
  }

  function getUpdater(set: ReturnType<typeof vi.fn>) {
    const updater = set.mock.calls[0]?.[0];
    return typeof updater === 'function'
      ? updater(makeBasicState())
      : updater || {};
  }

  describe('stream event', () => {
    it('creates new message with content and streamingId', () => {
      const set = vi.fn();
      const get = vi.fn(() => modelS(makeBasicState()));

      function modelS(s: ReturnType<typeof makeBasicState>) {
        return {
          ...s,
          currentRunId: s.currentRunId,
          streamingId: null as string | null,
          messages: [] as typeof s.messages,
          currentRole: null as string | null,
          continuingId: null as string | null,
          pendingVersions: null as string[] | null,
          pendingThinkingVersions: null as string[] | null,
        };
      }

      const handler = createStreamHandler(set as never, get as never);
      handler({ type: 'stream', content: 'new chunk', agent_name: 'Bot' });

      const updater = set.mock.calls[0]?.[0];
      if (typeof updater === 'function') {
        const state = modelS(makeBasicState());
        const result = updater(state);
        expect(result.streamingId).toBeDefined();
        expect(result.messages).toHaveLength(1);
        expect(result.wsStatus).toBe('connected');
      }
    });
  });

  describe('thinking_stream event', () => {
    it('calls set to update thinking for streaming message', () => {
      const set = vi.fn();
      const get = vi.fn(() => ({
        ...makeBasicState(),
        streamingId: 'stream-1',
        messages: [
          {
            id: 'stream-1',
            role: 'agent',
            content: 'Hello',
            thinking: '',
            agent_name: 'Agent',
            round_number: 0,
            created_at: new Date().toISOString(),
          },
        ],
        currentRunId: 'run-1',
        continuingId: null,
        pendingVersions: null,
        pendingThinkingVersions: null,
      }));

      const handler = createStreamHandler(set as never, get as never);
      handler({
        type: 'thinking_stream',
        content: 'thinking chunk',
        agent_name: 'Bot',
      });

      const updater = set.mock.calls[0]?.[0];
      if (typeof updater === 'function') {
        const state = {
          streamingId: 'stream-1',
          messages: [
            {
              id: 'stream-1',
              role: 'agent',
              content: 'Hello',
              thinking: '',
              agent_name: 'Agent',
            },
          ],
          currentRunId: 'run-1',
          continuingId: null,
          pendingVersions: null,
          pendingThinkingVersions: null,
        };
        const result = updater(state);
        expect(result.messages[0].thinking).toBe('thinking chunk');
      }
    });
  });

  describe('message event', () => {
    it('updates content of streaming message', () => {
      const set = vi.fn();
      const get = vi.fn(() => makeBasicState());

      const handler = createStreamHandler(set as never, get as never);
      handler({
        type: 'message',
        content: 'Updated',
        thinking: 'new thinking',
        role: 'agent',
      });

      const updater = set.mock.calls[0]?.[0];
      if (typeof updater === 'function') {
        const s = makeBasicState();
        const result = updater(s);
        const msgs = result.messages as Array<{
          id: string;
          content: string;
          thinking: string;
        }>;
        expect(msgs.find((m) => m.id === 'stream-1')?.content).toBe('Updated');
        expect(result.currentRole).toBe('agent');
        expect(result.wsStatus).toBe('connected');
      }
    });

    it('creates new message when no streamingId', () => {
      const set = vi.fn();
      const get = vi.fn(() => ({ ...makeBasicState(), streamingId: null }));

      const handler = createStreamHandler(set as never, get as never);
      handler({
        type: 'message',
        content: 'New msg',
        thinking: undefined,
        role: 'assistant',
        agent_name: 'Bot',
        round_number: 1,
      });

      const updater = set.mock.calls[0]?.[0];
      if (typeof updater === 'function') {
        const s = { ...makeBasicState(), streamingId: null };
        const result = updater(s);
        const msgs = result.messages as Array<{
          role: string;
          content: string;
          agent_name: string;
        }>;
        expect(msgs).toHaveLength(2);
        expect(msgs[1].role).toBe('assistant');
        expect(msgs[1].content).toBe('New msg');
      }
    });
  });

  describe('thinking_done event', () => {
    it('marks streaming message as thinking done', () => {
      const set = vi.fn();
      const get = vi.fn(() => makeBasicState());

      const handler = createStreamHandler(set as never, get as never);
      handler({ type: 'thinking_done', agent_name: 'Agent' });

      const updater = set.mock.calls[0]?.[0];
      if (typeof updater === 'function') {
        const s = makeBasicState();
        const result = updater(s);
        const msgs = result.messages as Array<{
          id: string;
          thinkingDone?: boolean;
        }>;
        expect(msgs.find((m) => m.id === 'stream-1')?.thinkingDone).toBe(true);
      }
    });
  });

  describe('info event', () => {
    it('appends info to streaming message content', () => {
      const set = vi.fn();
      const get = vi.fn(() => makeBasicState());

      const handler = createStreamHandler(set as never, get as never);
      handler({
        type: 'info',
        content: 'Fetching data...',
        data: 'extra info',
      });

      const updater = set.mock.calls[0]?.[0];
      if (typeof updater === 'function') {
        const s = makeBasicState();
        const result = updater(s);
        const msgs = result.messages as Array<{ id: string; content: string }>;
        const streamMsg = msgs.find((m) => m.id === 'stream-1');
        expect(streamMsg?.content).toContain('[extra info]');
      }
    });

    it('returns empty state when no streamingId', () => {
      const set = vi.fn();
      const get = vi.fn(() => ({ ...makeBasicState(), streamingId: null }));

      const handler = createStreamHandler(set as never, get as never);
      handler({ type: 'info', content: 'some info', data: undefined });

      const updater = set.mock.calls[0]?.[0];
      if (typeof updater === 'function') {
        const s = { ...makeBasicState(), streamingId: null };
        const result = updater(s);
        expect(result).toEqual({});
      }
    });
  });

  describe('error event', () => {
    it('sets status=error with error message', () => {
      const set = vi.fn();
      const get = vi.fn(() => makeBasicState());

      const handler = createStreamHandler(set as never, get as never);
      handler({ type: 'error', content: 'Something went wrong' });

      const result = getUpdater(set);
      expect(result.status).toBe('error');
      expect(result.error).toBe('Something went wrong');
    });

    it('uses default error message when no content', () => {
      const set = vi.fn();
      const get = vi.fn(() => makeBasicState());

      const handler = createStreamHandler(set as never, get as never);
      handler({ type: 'error' });

      const result = getUpdater(set);
      expect(result.status).toBe('error');
      expect(result.error).toBe('Unknown error');
    });
  });

  describe('balance_warning event', () => {
    it('sets error with warning message', () => {
      const set = vi.fn();
      const get = vi.fn(() => ({
        ...makeBasicState(),
        currentRunId: 'run-1',
        streamingId: null,
        continuingId: null,
        pendingVersions: null,
        pendingThinkingVersions: null,
      }));

      const handler = createStreamHandler(set as never, get as never);
      handler({ type: 'balance_warning', content: '余额不足' });

      const result = getUpdater(set);
      expect(result.status).toBe('error');
      expect(result.error).toBe('余额不足');
    });
  });
});
