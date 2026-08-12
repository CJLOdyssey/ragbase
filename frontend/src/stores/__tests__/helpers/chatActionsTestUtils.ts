import type { ChatMessage } from '../../../types';
import { vi } from 'vitest';

// Shared mock fns for the chatActions test files. NOTE: plain vi.fn() exports
// (NOT vi.hoisted) — vitest 4 forbids exporting hoisted variables
// ("Cannot export hoisted variable"). Test files must import this module FIRST
// (before ../chatActions) so the mocks are initialized before any vi.mock
// factory that references them runs.
export const mockListKeys = vi.fn().mockResolvedValue([
  {
    id: 'key-1',
    is_default: true,
    is_active: true,
    models: ['deepseek-chat'],
  },
]);

export const mockSubmitReq = vi.fn().mockResolvedValue({
  run_id: 'run-1',
  status: 'running',
  session_id: 'sess-1',
});

export const mockResumeRun = vi.fn().mockResolvedValue({
  run_id: 'run-2',
  status: 'running',
  session_id: 'sess-1',
});

export function makeMsg(overrides: Partial<ChatMessage> = {}): ChatMessage {
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

export const initialState = {
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

// beforeEach body shared by the chatActions test files. chatStore is imported
// dynamically so that importing this module does NOT pull in chatStore (and
// thereby api/client) before the test file's vi.mock factories are registered.
export async function resetMockDefaults(): Promise<void> {
  const { useChatStore } = await import('../../chatStore');
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
}
