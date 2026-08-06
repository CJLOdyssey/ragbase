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

function bumpLastVersion(
  versions: string[] | null | undefined,
  replacement: string,
): string[] | undefined {
  if (!versions || versions.length === 0) return versions ?? undefined;
  const next = [...versions];
  next[next.length - 1] = replacement;
  return next;
}

// Edit-regenerate: the new answer REPLACES the target message. Old content
// is archived into versions; the stream starts fresh (not old+new).
function startEditBranch(
  s: ChatState,
  msg: StreamBranchMsg,
  chunk: string,
  newId: string,
  chunkInContent: boolean,
): Partial<ChatState> {
  const targetIdx = s.messages.findIndex((m) => m.id === s.editTargetId);
  const oldMsg = targetIdx >= 0 ? s.messages[targetIdx] : null;
  const oldContent = oldMsg?.content || '';
  const oldThinking = oldMsg?.thinking || '';
  const newVersions = oldMsg?.versions
    ? [...oldMsg.versions, oldContent]
    : [oldContent];
  const newThinkingVersions = oldMsg?.thinkingVersions
    ? [...oldMsg.thinkingVersions, oldThinking]
    : oldThinking
      ? [oldThinking]
      : undefined;
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
        versions: newVersions,
        thinkingVersions: newThinkingVersions,
        currentVersion: newVersions.length - 1,
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
        versions: bumpLastVersion(s.pendingVersions, oldContent),
        thinkingVersions: bumpLastVersion(
          s.pendingThinkingVersions,
          chunkInContent ? oldThinking : oldThinking + chunk,
        ),
        currentVersion: s.pendingVersions
          ? s.pendingVersions.length - 1
          : undefined,
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
  const pending = s.pendingVersions;
  const pendingThinking = s.pendingThinkingVersions;
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
        versions: pending ? [...pending, chunk] : undefined,
        thinkingVersions: pendingThinking
          ? [...pendingThinking, '']
          : undefined,
        currentVersion: pending ? pending.length : undefined,
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
  const pending = s.pendingVersions;
  const pendingThinking = s.pendingThinkingVersions;
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
        versions: pending ? [...pending, ''] : undefined,
        thinkingVersions: pendingThinking
          ? [...pendingThinking, chunk]
          : undefined,
        currentVersion: pending ? pending.length : undefined,
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
