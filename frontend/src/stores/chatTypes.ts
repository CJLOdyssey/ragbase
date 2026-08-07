import type { AppStatus, ChatMessage, RunResult } from '../types';

export type WsConnectionStatus =
  'disconnected' | 'connecting' | 'connected' | 'reconnecting';

export interface ChatState {
  currentRunId: string | null;
  currentSessionId: string | null;
  currentConvId: string | null;
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
  switchUserVersion: (msgId: string, direction: 'prev' | 'next') => void;
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
    convId?: string | null,
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
  /** runId → agent turn (content/thinking) — 分页版本切换时模型消息联动 */
  runTurns: Record<string, { content: string; thinking: string }>;
  setRunTurns: (
    turns: Record<string, { content: string; thinking: string }>,
  ) => void;
  reset: () => void;
}
