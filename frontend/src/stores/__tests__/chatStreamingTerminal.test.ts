import { createStreamHandler } from '../chatStreaming';
import { useApprovalStore } from '../streamHandler';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../utils/logger', () => ({
  default: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
}));

vi.mock('./uid', () => ({ uid: vi.fn(() => 'test-uid') }));

describe('chatStreaming terminal events', { tags: ['unit'] }, () => {
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

  describe('open_url event', () => {
    it('dispatches browser-open-url event with the URL', () => {
      const set = vi.fn();
      const get = vi.fn(() => makeBasicState());
      const dispatched: string[] = [];
      const listener = (e: Event) =>
        dispatched.push((e as CustomEvent<string>).detail);
      window.addEventListener('browser-open-url', listener);

      const handler = createStreamHandler(set as never, get as never);
      handler({ type: 'open_url', url: 'https://example.com' });

      expect(dispatched).toEqual(['https://example.com']);
      window.removeEventListener('browser-open-url', listener);
    });

    it('does nothing if url is missing', () => {
      const set = vi.fn();
      const get = vi.fn(() => makeBasicState());
      const dispatched: string[] = [];
      const listener = (e: Event) =>
        dispatched.push((e as CustomEvent<string>).detail);
      window.addEventListener('browser-open-url', listener);

      const handler = createStreamHandler(set as never, get as never);
      handler({ type: 'open_url' });

      expect(dispatched).toEqual([]);
      window.removeEventListener('browser-open-url', listener);
    });
  });

  describe('result event', () => {
    it('sets status to idle and stores result', () => {
      const set = vi.fn();
      const get = vi.fn(() => ({
        ...makeBasicState(),
        currentRunId: 'run-1',
        streamingId: 'stream-1',
        continuingId: null,
        pendingVersions: null,
        pendingThinkingVersions: null,
      }));

      const handler = createStreamHandler(set as never, get as never);
      handler({ type: 'result', code: 'print("hello")' });

      const updater = set.mock.calls[0]?.[0];
      if (typeof updater === 'function') {
        const s = {
          ...makeBasicState(),
          streamingId: 'stream-1',
          currentRunId: 'run-1',
          messages: [
            {
              id: 'stream-1',
              role: 'agent' as const,
              content: 'Hello',
              thinking: '',
              agent_name: 'Agent',
              round_number: 0,
              created_at: new Date().toISOString(),
            },
          ],
          continuingId: null,
          pendingVersions: null,
          pendingThinkingVersions: null,
        };
        const result = updater(s);
        expect(result.status).toBe('idle');
        expect(result.streamingId).toBeNull();
        expect(result.result).toBeDefined();
      }
    });
  });

  describe('team_result event', () => {
    it('sets status to idle', () => {
      const set = vi.fn();
      const get = vi.fn(() => ({
        ...makeBasicState(),
        currentRunId: 'run-1',
        streamingId: 'stream-1',
        continuingId: null,
        pendingVersions: null,
        pendingThinkingVersions: null,
      }));

      const handler = createStreamHandler(set as never, get as never);
      handler({ type: 'team_result' });

      const updater = set.mock.calls[0]?.[0];
      if (typeof updater === 'function') {
        const s = {
          ...makeBasicState(),
          streamingId: 'stream-1',
          currentRunId: 'run-1',
          messages: [
            {
              id: 'stream-1',
              role: 'agent' as const,
              content: 'Hello',
              thinking: '',
              agent_name: 'Agent',
              round_number: 0,
              created_at: new Date().toISOString(),
            },
          ],
          continuingId: null,
          pendingVersions: null,
          pendingThinkingVersions: null,
        };
        const result = updater(s);
        expect(result.status).toBe('idle');
        expect(result.streamingId).toBeNull();
      }
    });
  });

  describe('thumbs event', () => {
    it('updates message thumbs feedback', () => {
      const set = vi.fn();
      const get = vi.fn(() => makeBasicState());

      const handler = createStreamHandler(set as never, get as never);
      handler({ type: 'thumbs', msgId: 'stream-1', value: 'up' });

      const updater = set.mock.calls[0]?.[0];
      if (typeof updater === 'function') {
        const s = makeBasicState();
        const result = updater(s);
        const msgs = result.messages as Array<{ id: string; thumbs?: string }>;
        expect(msgs.find((m) => m.id === 'stream-1')?.thumbs).toBe('up');
      }
    });

    it('does not modify unrelated messages', () => {
      const set = vi.fn();
      const get = vi.fn(() => ({
        ...makeBasicState(),
        messages: [
          {
            id: 'other-msg',
            role: 'agent' as const,
            content: 'Other',
            thinking: '',
            agent_name: 'Agent',
            round_number: 0,
            created_at: new Date().toISOString(),
          },
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
      }));

      const handler = createStreamHandler(set as never, get as never);
      handler({ type: 'thumbs', msgId: 'stream-1', value: 'down' });

      const updater = set.mock.calls[0]?.[0];
      if (typeof updater === 'function') {
        const s = {
          ...makeBasicState(),
          messages: [
            {
              id: 'other-msg',
              role: 'agent',
              content: 'Other',
              agent_name: 'Agent',
            },
            {
              id: 'stream-1',
              role: 'agent',
              content: 'Hello',
              agent_name: 'Agent',
            },
          ],
          currentRunId: 'run-1',
          streamingId: 'stream-1',
          continuingId: null,
          pendingVersions: null,
          pendingThinkingVersions: null,
          currentRole: null,
        };
        const result = updater(s);
        const msgs = result.messages as Array<{ id: string; thumbs?: string }>;
        expect(
          msgs.find(
            (m: { id: string; thumbs?: string }) => m.id === 'other-msg',
          )?.thumbs,
        ).toBeUndefined();
        expect(
          msgs.find((m: { id: string; thumbs?: string }) => m.id === 'stream-1')
            ?.thumbs,
        ).toBe('down');
      }
    });
  });

  describe('team_result verdicts', () => {
    it('attaches verdicts and total rounds to messages', () => {
      const set = vi.fn();
      const get = vi.fn(() => ({
        ...makeBasicState(),
        currentRunId: 'run-1',
        streamingId: 'stream-1',
        continuingId: null,
        pendingVersions: null,
        pendingThinkingVersions: null,
      }));

      const handler = createStreamHandler(set as never, get as never);
      handler({
        type: 'team_result',
        display: 'done',
        verdicts: { writer: { role: 'writer', approved: true, rounds: 2 } },
        rounds: 2,
      });

      const updater = set.mock.calls[1]?.[0];
      if (typeof updater === 'function') {
        const s = {
          ...makeBasicState(),
          streamingId: null,
          messages: [
            {
              id: 'stream-1',
              role: 'agent' as const,
              content: 'done',
              agent_name: 'writer',
              round_number: 0,
              created_at: new Date().toISOString(),
            },
          ],
        };
        const result = updater(s);
        const msgs = result.messages as Array<{
          id: string;
          verdicts?: Record<
            string,
            { role: string; approved: boolean; rounds: number }
          >;
          round?: number;
        }>;
        expect(msgs.find((m) => m.id === 'stream-1')?.verdicts?.writer).toEqual(
          { role: 'writer', approved: true, rounds: 2 },
        );
        expect(msgs.find((m) => m.id === 'stream-1')?.round).toBe(2);
      }
    });

    it('does not attach when verdicts missing', () => {
      const set = vi.fn();
      const get = vi.fn(() => makeBasicState());

      const handler = createStreamHandler(set as never, get as never);
      handler({ type: 'team_result', display: 'done' });

      expect(set).toHaveBeenCalledTimes(1);
    });
  });

  describe('approval_request event', () => {
    it('sets approval store request and tags the streaming message', () => {
      const set = vi.fn();
      const get = vi.fn(() => ({
        ...makeBasicState(),
        currentRunId: 'run-1',
        streamingId: 'stream-1',
        continuingId: null,
        pendingVersions: null,
        pendingThinkingVersions: null,
      }));

      const handler = createStreamHandler(set as never, get as never);
      handler({ type: 'approval_request', run_id: 'run-1', node: 'reviewer' });

      expect(useApprovalStore.getState().request).toEqual({
        runId: 'run-1',
        node: 'reviewer',
      });
      const updater = set.mock.calls[0]?.[0];
      if (typeof updater === 'function') {
        const s = { ...makeBasicState(), streamingId: 'stream-1' };
        const result = updater(s);
        const msgs = result.messages as Array<{
          id: string;
          approvalRequest?: { runId: string; node: string };
        }>;
        expect(msgs.find((m) => m.id === 'stream-1')?.approvalRequest).toEqual({
          runId: 'run-1',
          node: 'reviewer',
        });
      }
      useApprovalStore.getState().setRequest(null);
    });

    it('ignores approval_request without run_id', () => {
      const set = vi.fn();
      const get = vi.fn(() => makeBasicState());

      const handler = createStreamHandler(set as never, get as never);
      handler({ type: 'approval_request', node: 'reviewer' });

      expect(set).not.toHaveBeenCalled();
      expect(useApprovalStore.getState().request).toBeNull();
    });
  });
});
