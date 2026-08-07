import type { ChatMessage } from '../types';
import Logger from '../utils/logger';
import { create } from 'zustand';
import type { ChatState } from './chatTypes';
import { uid } from './uid';
import type {
  TeamVerdict,
  WsApprovalRequestEvent,
  WsStreamEvent,
  WsTeamResultEvent,
  WsThinkingStreamEvent,
} from './wsEvents';

type SetFn = (fn: (state: ChatState) => Partial<ChatState>) => void;
type GetFn = () => ChatState;

interface ApprovalRequest {
  runId: string;
  node: string;
}

interface ApprovalStoreState {
  request: ApprovalRequest | null;
  setRequest: (request: ApprovalRequest | null) => void;
}

export const useApprovalStore = create<ApprovalStoreState>((set) => ({
  request: null,
  setRequest: (request) => set({ request }),
}));

type TeamMessageMeta = ChatMessage & {
  verdicts?: Record<string, TeamVerdict>;
  round?: number;
  approvalRequest?: ApprovalRequest;
};

export function handleTeamResultMeta(set: SetFn, msg: WsTeamResultEvent): void {
  const verdicts = msg.verdicts;
  const rounds = msg.rounds;
  if (!verdicts || typeof verdicts !== 'object' || Array.isArray(verdicts))
    return;
  set((s) => ({
    messages: s.messages.map(
      (m) =>
        ({
          ...m,
          verdicts,
          ...(rounds !== undefined ? { round: rounds } : {}),
        }) as TeamMessageMeta,
    ),
  }));
}

export function handleApprovalRequest(
  set: SetFn,
  msg: WsApprovalRequestEvent,
): void {
  const runId = msg.run_id;
  const node = msg.node;
  if (!runId || !node) return;
  useApprovalStore.getState().setRequest({ runId, node });
  set((s) => {
    const targetId = s.streamingId || s.messages[s.messages.length - 1]?.id;
    if (!targetId) return {};
    return {
      messages: s.messages.map((m) =>
        m.id === targetId
          ? ({ ...m, approvalRequest: { runId, node } } as TeamMessageMeta)
          : m,
      ),
    };
  });
}

type StreamBranchMsg = { agent_name?: string };

// Edit-regenerate: the new answer REPLACES the target message. The old message
// keeps its id remapped to the new run's message id; the stream starts fresh.
function startEditBranch(
  s: ChatState,
  msg: StreamBranchMsg,
  chunk: string,
  newId: string,
  chunkInContent: boolean,
): Partial<ChatState> {
  return {
    streamingId: newId,
    editTargetId: null,
    continuingId: null,
    pendingVersions: null,
    pendingThinkingVersions: null,
    skipThinking: false,
    messages: s.messages.map((m) => {
      if (m.id !== s.editTargetId) return m;
      return {
        ...m,
        id: newId,
        content: chunkInContent ? chunk : '',
        thinking: chunkInContent ? '' : chunk,
        runId: s.currentRunId ?? m.runId,
      };
    }),
    currentRole: msg.agent_name || 'Agent',
    wsStatus: 'connected' as ChatState['wsStatus'],
  };
}

function startContinueBranch(
  s: ChatState,
  msg: StreamBranchMsg,
  chunk: string,
  newId: string,
  chunkInContent: boolean,
): Partial<ChatState> {
  const contIdx = s.messages.findIndex((m) => m.id === s.continuingId);
  const oldMsg = contIdx >= 0 ? s.messages[contIdx] : null;
  const oldContent = oldMsg?.content || '';
  const oldThinking = oldMsg?.thinking || '';
  const base = contIdx >= 0 ? s.messages.slice(0, contIdx) : s.messages;
  const agentName = oldMsg?.agent_name || msg.agent_name || 'Agent';
  return {
    streamingId: newId,
    continuingId: null,
    pendingVersions: null,
    pendingThinkingVersions: null,
    skipThinking: false,
    messages: [
      ...base,
      {
        id: newId,
        role: 'agent',
        agent_name: agentName,
        content: chunkInContent ? oldContent + chunk : oldContent,
        thinking: chunkInContent ? oldThinking : oldThinking + chunk,
        round_number: 0,
        created_at: new Date().toISOString(),
      },
    ],
    currentRole: msg.agent_name || 'Agent',
    wsStatus: 'connected' as ChatState['wsStatus'],
  };
}

function startFreshStream(
  s: ChatState,
  msg: StreamBranchMsg,
  chunk: string,
  newId: string,
): Partial<ChatState> {
  return {
    streamingId: newId,
    pendingVersions: null,
    pendingThinkingVersions: null,
    skipThinking: false,
    messages: [
      ...s.messages,
      {
        id: newId,
        role: 'agent',
        agent_name: msg.agent_name || 'Agent',
        content: chunk,
        thinking: '',
        round_number: 0,
        created_at: new Date().toISOString(),
        runId: s.currentRunId ?? undefined,
      },
    ],
    currentRole: msg.agent_name || 'Agent',
    wsStatus: 'connected' as ChatState['wsStatus'],
  };
}

function startFreshThinking(
  s: ChatState,
  msg: StreamBranchMsg,
  chunk: string,
  newId: string,
): Partial<ChatState> {
  return {
    streamingId: newId,
    continuingId: null,
    pendingVersions: null,
    pendingThinkingVersions: null,
    messages: [
      ...s.messages,
      {
        id: newId,
        role: 'agent',
        agent_name: msg.agent_name || 'Agent',
        content: '',
        thinking: chunk,
        round_number: 0,
        created_at: new Date().toISOString(),
        runId: s.currentRunId ?? undefined,
      },
    ],
    currentRole: msg.agent_name || 'Agent',
    wsStatus: 'connected' as ChatState['wsStatus'],
  };
}

export function handleStreamStart(
  s: ChatState,
  msg: WsStreamEvent,
  chunk: string,
): Partial<ChatState> {
  const newId = crypto.randomUUID?.() || uid();
  if (s.editTargetId) {
    Logger.info(
      '[chat] edit stream — merging into target msg %s',
      s.editTargetId,
    );
    return startEditBranch(s, msg, chunk, newId, true);
  }
  if (s.continuingId) {
    Logger.info(
      '[chat] continue stream — replacing interrupted msg (continuingId=%s, newId=%s)',
      s.continuingId,
      newId,
    );
    return startContinueBranch(s, msg, chunk, newId, true);
  }
  return startFreshStream(s, msg, chunk, newId);
}

export function handleThinkingStreamNew(
  s: ChatState,
  msg: WsThinkingStreamEvent,
  chunk: string,
): Partial<ChatState> {
  const newId = crypto.randomUUID?.() || uid();
  if (s.editTargetId) {
    return startEditBranch(s, msg, chunk, newId, false);
  }
  if (s.continuingId) {
    return startContinueBranch(s, msg, chunk, newId, false);
  }
  return startFreshThinking(s, msg, chunk, newId);
}

export function handleStreamEvent(
  set: SetFn,
  get: GetFn,
  activeStreamMsgIds: Set<string>,
  msg: WsStreamEvent,
): void {
  const chunk = msg.content || '';
  if (!chunk) return;
  const s = get();
  const runId = s.currentRunId || '';
  // Continuation is only valid while a message is streaming: a leftover run id
  // (result event lost / state reset mid-run) must not swallow the first chunk.
  if (runId && activeStreamMsgIds.has(runId) && s.streamingId) {
    set((prev) => {
      if (!prev.streamingId) return {};
      return {
        skipThinking: false,
        messages: prev.messages.map((m) => {
          if (m.id !== prev.streamingId) return m;
          return {
            ...m,
            content: m.content + chunk,
            thinking: m.thinking ?? '',
          };
        }),
        currentRole: msg.agent_name || 'Agent',
        wsStatus: 'connected' as ChatState['wsStatus'],
      };
    });
    return;
  }
  activeStreamMsgIds.add(runId);
  // If streamingId already set (from prior thinking_stream), use that message
  if (s.streamingId) {
    set((prev) => {
      if (!prev.streamingId) return {};
      return {
        skipThinking: false,
        messages: prev.messages.map((m) => {
          if (m.id !== prev.streamingId) return m;
          return {
            ...m,
            content: m.content + chunk,
            thinking: m.thinking ?? '',
          };
        }),
        currentRole: msg.agent_name || 'Agent',
        wsStatus: 'connected' as ChatState['wsStatus'],
      };
    });
    return;
  }
  set((prev) => {
    return handleStreamStart(prev, msg, chunk);
  });
}

export function handleThinkingStreamEvent(
  set: SetFn,
  get: GetFn,
  activeStreamMsgIds: Set<string>,
  msg: WsThinkingStreamEvent,
): void {
  const chunk = msg.content || '';
  if (!chunk) return;
  const s = get();
  Logger.info(
    '[chat] thinking stream entry — editTargetId=%s streamingId=%s runId=%s',
    s.editTargetId,
    s.streamingId,
    s.currentRunId,
  );
  const runId = s.currentRunId || '';
  if (runId && activeStreamMsgIds.has(runId) && s.streamingId) {
    set((prev) => {
      if (!prev.streamingId) return {};
      return {
        messages: prev.messages.map((m) => {
          if (m.id !== prev.streamingId) return m;
          return { ...m, thinking: (m.thinking ?? '') + chunk };
        }),
      };
    });
    return;
  }
  activeStreamMsgIds.add(runId);
  set((s) => {
    if (s.streamingId) {
      return {
        messages: s.messages.map((m) => {
          if (m.id !== s.streamingId) return m;
          const updatedThinking = (m.thinking ?? '') + chunk;
          return { ...m, thinking: updatedThinking };
        }),
      };
    }
    return handleThinkingStreamNew(s, msg, chunk);
  });
}
