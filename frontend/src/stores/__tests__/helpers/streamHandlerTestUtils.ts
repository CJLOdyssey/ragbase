export function makeMsg(id: string, overrides: Record<string, unknown> = {}) {
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

export function makeState(overrides: Record<string, unknown> = {}) {
  return {
    currentRunId: 'run-1',
    streamingId: null,
    messages: [],
    status: 'running',
    currentRole: null,
    wsStatus: 'connected',
    skipThinking: false,
    continuingId: null,
    pendingVersions: null,
    pendingThinkingVersions: null,
    ...overrides,
  };
}
