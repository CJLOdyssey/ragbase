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

function buildReplacementMessage(
  newId: string,
  agentName: string,
  content: string,
  thinking: string,
): ChatMessage {
  return {
    id: newId,
    role: 'agent',
    agent_name: agentName,
    content,
    thinking,
    round_number: 0,
    created_at: new Date().toISOString(),
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
    // 重新生成完成：给新模型消息挂答案分页（同 requirement 答案组 =
    // 旧 run 列表 + 新 run），切换走分支加载（父链 + 子孙链）。
    let pendingRegenerate = _s.pendingRegenerate;
    const done = msgs.find((m) => m.id === _s.streamingId);
    if (done && pendingRegenerate && runId) {
      const answerRunIds = [...pendingRegenerate.oldRunIds, runId];
      msgs = msgs.map((m) =>
        m.id === done.id
          ? {
              ...m,
              userMsgId: pendingRegenerate!.userMsgId,
              answerVersions: answerRunIds.map(
                () => pendingRegenerate!.requirement,
              ),
              answerRunIds,
              currentAnswerVersion: answerRunIds.length - 1,
            }
          : m,
      );
      pendingRegenerate = null;
    }
    return {
      messages: msgs,
      pendingRegenerate,
      status: 'idle' as ChatState['status'],
      streamingId: null,
      // 续写/生成完成：清除中断标记，避免「已中断/继续」按钮永久残留
      // （否则用户可无限次继续 → 每次续写 run 的思考都追加，思考内容爆炸）。
      interruptedMessageId: null,
      result: makeRunResult(codeContent),
      skipThinking: false,
    };
  });
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
