import { updateAnswerVersions } from '../api/client/sessions';
import type { ChatMessage, RunResult } from '../types';
import Logger from '../utils/logger';
import type { ChatState } from './chatTypes';
import { uid } from './uid';
import type {
  WsResultEvent,
  WsTeamResultEvent,
  WsThinkingDoneEvent,
  WsThumbsEvent,
} from './wsEvents';

function makeRunResult(code: string): RunResult {
  return {
    code,
    requirement: '',
    pm_document: '',
    review: '',
    approved: false,
    status: 'completed',
  };
}

type SetFn = (fn: (state: ChatState) => Partial<ChatState>) => void;
type GetFn = () => ChatState;

function bumpLastVersion(
  versions: string[] | null | undefined,
  replacement: string,
): string[] | undefined {
  if (!versions || versions.length === 0) return versions ?? undefined;
  const next = [...versions];
  next[next.length - 1] = replacement;
  return next;
}

function buildReplacementMessage(
  newId: string,
  agentName: string,
  content: string,
  thinking: string,
  versions: string[] | undefined,
  thinkingVersions: string[] | undefined,
): ChatMessage {
  return {
    id: newId,
    role: 'agent',
    agent_name: agentName,
    content,
    thinking,
    round_number: 0,
    created_at: new Date().toISOString(),
    versions,
    thinkingVersions,
    currentVersion: versions ? versions.length - 1 : undefined,
  };
}

function findContinuingTarget(
  s: ChatState,
  continuingId: string,
): { oldMsg: ChatMessage | null; base: ChatMessage[] } {
  const contIdx = s.messages.findIndex((m) => m.id === continuingId);
  const oldMsg = contIdx >= 0 ? s.messages[contIdx] : null;
  const base =
    contIdx >= 0
      ? s.messages.slice(0, contIdx)
      : s.messages.filter((m) => m.id !== continuingId);
  return { oldMsg, base };
}

export function handleThinkingDone(
  s: ChatState,
  msg: WsThinkingDoneEvent,
): Partial<ChatState> {
  if (!s.continuingId) {
    return {};
  }
  Logger.warn(
    '[chat] continue thinking_done — no streamingId; falling back to direct replacement (continuingId=%s)',
    s.continuingId,
  );
  const { oldMsg, base } = findContinuingTarget(s, s.continuingId);
  const newId = crypto.randomUUID?.() || uid();
  const oldContent = oldMsg?.content || '';
  const oldThinking = oldMsg?.thinking || '';
  const thinking = msg.thinking || oldThinking;
  return {
    streamingId: newId,
    continuingId: null,
    pendingVersions: null,
    pendingThinkingVersions: null,
    messages: [
      ...base,
      buildReplacementMessage(
        newId,
        oldMsg?.agent_name || msg.agent_name || 'Agent',
        oldContent,
        thinking,
        bumpLastVersion(s.pendingVersions, oldContent),
        bumpLastVersion(s.pendingThinkingVersions, thinking),
      ),
    ],
    currentRole: msg.agent_name || 'Agent',
    wsStatus: 'connected' as ChatState['wsStatus'],
  };
}

export function handleThinkingDoneEvent(
  set: SetFn,
  msg: WsThinkingDoneEvent,
): void {
  set((s) => {
    if (s.streamingId) {
      return {
        messages: s.messages.map((m) =>
          m.id === s.streamingId
            ? {
                ...m,
                thinkingDone: true,
                ...(msg.thinking ? { thinking: msg.thinking } : {}),
              }
            : m,
        ),
      };
    }
    return handleThinkingDone(s, msg);
  });
}

export function handleResultEvent(
  set: SetFn,
  get: GetFn,
  activeStreamMsgIds: Set<string>,
  msg: WsResultEvent,
): void {
  const runId = get().currentRunId;
  const streamMsgId = get().streamingId;
  const codeContent: string = msg.code ? String(msg.code) : '';
  set((_s) => {
    let msgs = _s.messages;
    if (_s.streamingId) {
      msgs = _s.messages.map((m) => {
        if (m.id !== _s.streamingId) return m;
        const updated: Record<string, unknown> = {};
        if (codeContent) updated.content = codeContent;
        if (m.thinking === '') updated.thinking = undefined;
        return { ...m, ...updated, thinkingDone: true } as ChatMessage;
      });
    }
    return {
      messages: msgs,
      status: 'idle' as ChatState['status'],
      streamingId: null,
      result: makeRunResult(codeContent),
      skipThinking: false,
    };
  });
  // Edit-regenerate: persist the merged answer versions so they survive a reload.
  if (streamMsgId && runId) {
    const done = get().messages.find((m) => m.id === streamMsgId);
    if (done && done.versions && done.versions.length > 0) {
      updateAnswerVersions(runId, done.versions, done.thinkingVersions).catch(
        (err) => {
          Logger.warn(
            '[chat] failed to persist answer versions for run %s: %s',
            runId,
            String(err),
          );
        },
      );
    }
  }
  Logger.info('[chat] result received — status set to idle');
  activeStreamMsgIds.delete(runId || '');
}

export function handleTeamResultEvent(
  set: SetFn,
  get: GetFn,
  activeStreamMsgIds: Set<string>,
  msg: WsTeamResultEvent,
): void {
  const runId = get().currentRunId;
  const display =
    typeof msg.display === 'string' && msg.display.trim() ? msg.display : '';
  const artifactCount =
    msg.artifacts &&
    typeof msg.artifacts === 'object' &&
    !Array.isArray(msg.artifacts)
      ? Object.keys(msg.artifacts).length
      : 0;
  set((_s) => {
    let msgs = _s.messages;
    if (_s.streamingId) {
      msgs = _s.messages.map((m) => {
        if (m.id !== _s.streamingId) return m;
        // Replace the unlabeled concatenated stream output with the composed
        // per-node artifact blocks so each node's result is presented separately.
        const updated: Record<string, unknown> = { thinkingDone: true };
        if (display) updated.content = display;
        return { ...m, ...updated } as ChatMessage;
      });
    }
    return {
      messages: msgs,
      status: 'idle' as ChatState['status'],
      streamingId: null,
      skipThinking: false,
    };
  });
  Logger.info(
    '[chat] team_result received — surfaced %d node artifacts, status set to idle',
    artifactCount,
  );
  activeStreamMsgIds.delete(runId || '');
}

export function handleThumbsEvent(set: SetFn, msg: WsThumbsEvent): void {
  set((s) => ({
    messages: s.messages.map((m) =>
      m.id === msg.msgId ? { ...m, thumbs: msg.value } : m,
    ),
  }));
}
