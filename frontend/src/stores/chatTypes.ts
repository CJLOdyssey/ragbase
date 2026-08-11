import type { AppStatus, ChatMessage, RunResult } from '../types';

export type WsConnectionStatus =
  'disconnected' | 'connecting' | 'connected' | 'reconnecting';

/** 重新生成（regenerate）流式上下文：完成后给新模型消息挂答案分页 */
export interface RegeneratePending {
  userMsgId: string;
  oldRunIds: string[];
  requirement: string;
}

export interface ChatState {
  currentRunId: string | null;
  currentSessionId: string | null;
  messages: ChatMessage[];
  status: AppStatus;
  result: RunResult | null;
  currentRole: string | null;
  error: string | null;
  streamingId: string | null;
  lastAbandonedRunId: string | null;
  interruptedMessageId: string | null;
  continuingId: string | null;
  /** When set, the next streamed answer merges into this agent message as a new version (edit-regenerate) */
  editTargetId: string | null;
  skipThinking: boolean;
  pendingVersions: string[] | null;
  pendingThinkingVersions: string[] | null;
  /** 重新生成进行中（流式完成后给模型消息挂答案分页） */
  pendingRegenerate: RegeneratePending | null;
  setThumbsFeedback: (msgId: string, value: 'up' | 'down' | null) => void;
  wsStatus: WsConnectionStatus;
  /** Conversation ID at submission time */
  submissionConvId: string | null;

  restoreSession: (
    sessionId: string,
    runId: string,
    messages: ChatMessage[],
    result: RunResult | null,
    status: AppStatus,
  ) => void;
  loadConversation: (
    messages: ChatMessage[],
    sessionId?: string | null,
  ) => void;
  cancelRun: () => void;
  addMessage: (msg: import('../types').WsMessage & { id?: string }) => void;
  setStatus: (status: AppStatus) => void;
  setResult: (result: RunResult | null) => void;
  setError: (error: string | null) => void;
  setWsStatus: (wsStatus: WsConnectionStatus) => void;
  activeRunId: string | null;
  setActiveRunId: (runId: string | null) => void;
  /** 用户版本切换（分支语义）：返回目标 runId，null = 无变化 */
  resolveUserVersionTarget: (
    msgId: string,
    direction: 'prev' | 'next',
  ) => string | null;
  /** 模型答案分页（重新生成分支）：返回目标 runId，null = 无变化 */
  resolveAnswerVersionTarget: (
    msgId: string,
    direction: 'prev' | 'next',
  ) => string | null;
  reset: () => void;
  /** 切换会话时清空消息与流状态（保留 currentSessionId，由 loadConversation 更新）。 */
  clearMessages: () => void;
}
