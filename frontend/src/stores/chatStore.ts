import { cancelRun as cancelRunApi } from '../api/client';
import { disconnectRun } from '../api/websocket';
import type { AppStatus, ChatMessage, RunResult } from '../types';
import Logger from '../utils/logger';
import { create } from 'zustand';
import { releaseActiveStreamMsgIds } from './chatStreaming';
import type { ChatState } from './chatTypes';
import { uid } from './uid';

export type { WsConnectionStatus, ChatState } from './chatTypes';

const INITIAL_STATE = {
  currentRunId: null,
  activeRunId: null,
  currentSessionId: null,
  messages: [],
  status: 'idle' as AppStatus,
  result: null,
  currentRole: null,
  error: null,
  streamingId: null,
  lastAbandonedRunId: null,
  interruptedMessageId: null,
  continuingId: null,
  editTargetId: null,
  skipThinking: false,
  pendingVersions: null,
  pendingThinkingVersions: null,
  pendingRegenerate: null,
  wsStatus: 'disconnected' as ChatState['wsStatus'],
  submissionConvId: null,
};

// 版本分页通用计算：方向 → 合法索引（越界夹取），未变时返回 null。
function clampVersion(total: number, cur: number, direction: 'prev' | 'next') {
  const nv =
    direction === 'prev' ? Math.max(0, cur - 1) : Math.min(total - 1, cur + 1);
  return nv === cur ? null : nv;
}

export const useChatStore = create<ChatState>((set, get) => ({
  ...INITIAL_STATE,

  restoreSession: (
    sessionId: string,
    runId: string,
    messages: ChatMessage[],
    result: RunResult | null,
    status: AppStatus,
  ) => {
    set({
      currentSessionId: sessionId,
      currentRunId: runId,
      messages,
      result,
      status,
      error: null,
      currentRole:
        messages.length > 0 ? messages[messages.length - 1].role : null,
    });
  },

  loadConversation: (messages: ChatMessage[], sessionId?: string | null) => {
    const s = get();
    const prevRunId = s.currentRunId;
    if (prevRunId) {
      Logger.info(
        '[chat] loadConversation — disconnecting previous run %s',
        prevRunId,
      );
      disconnectRun(prevRunId);
      // 流式消息 id 记录随 run 结束释放，避免长会话无界累积。
      releaseActiveStreamMsgIds(prevRunId);
    }
    set({
      messages,
      currentSessionId: sessionId ?? null,
      currentRunId: null,
      activeRunId: null,
      streamingId: null,
      status: 'idle',
      wsStatus: 'disconnected',
      lastAbandonedRunId: prevRunId,
      error: null,
      skipThinking: false,
      continuingId: null,
      interruptedMessageId: null,
      submissionConvId: null,
    });
  },

  cancelRun: () => {
    const s = get();
    const prevRunId = s.currentRunId;
    const sid = s.streamingId;
    if (prevRunId) {
      Logger.info('[chat] cancelRun — cancelling run %s', prevRunId);
      disconnectRun(prevRunId);
      releaseActiveStreamMsgIds(prevRunId);
      // 真取消：通知后端终止任务并中断上游 LLM 流（fire-and-forget）。
      void cancelRunApi(prevRunId).catch((err) => {
        Logger.warn(
          '[chat] cancelRun API failed for %s: %s',
          prevRunId,
          String(err),
        );
      });
    }
    set({
      currentRunId: null,
      streamingId: null,
      status: 'idle',
      wsStatus: 'disconnected',
      interruptedMessageId: sid,
      continuingId: null,
      skipThinking: false,
    });
  },

  clearMessages: () => {
    const s = get();
    if (s.currentRunId) {
      Logger.info(
        '[chat] clearMessages — disconnecting run %s',
        s.currentRunId,
      );
      disconnectRun(s.currentRunId);
    }
    // 切换会话：立即清空旧消息与流状态，避免旧消息残留到新会话加载完成才跳变。
    // 保留 currentSessionId，由 loadConversation 在加载完成后更新。
    set({
      messages: [],
      currentRunId: null,
      activeRunId: null,
      streamingId: null,
      status: 'idle',
      wsStatus: 'disconnected',
      error: null,
      skipThinking: false,
      continuingId: null,
      interruptedMessageId: null,
    });
  },

  addMessage: (msg) => {
    set((s) => ({
      messages: [
        ...s.messages,
        {
          id: msg.id || uid(),
          role: msg.role!,
          agent_name: msg.agent_name || 'Agent',
          content: msg.content || '',
          thinking: msg.thinking,
          round_number: msg.round_number ?? 0,
          created_at: new Date().toISOString(),
        },
      ],
      currentRole: msg.role! || 'Agent',
    }));
  },

  setResult: (result) => set({ result }),
  setStatus: (status) => set({ status }),
  setError: (error) => set({ error }),
  setWsStatus: (wsStatus) => set({ wsStatus }),
  setActiveRunId: (runId) => set({ activeRunId: runId }),

  reset: () => {
    const s = get();
    if (s.currentRunId) {
      disconnectRun(s.currentRunId);
      releaseActiveStreamMsgIds(s.currentRunId);
    }
    set({ ...INITIAL_STATE, submissionConvId: null });
  },

  // 用户消息版本切换（分支语义）：计算目标 runId（越界夹取），null = 无变化。
  resolveUserVersionTarget: (msgId, direction) => {
    const msg = get().messages.find((m) => m.id === msgId);
    if (!msg) return null;
    const versions = msg.userVersions;
    const versionRunIds = msg.versionRunIds;
    if (!versions || versions.length < 2) return null;
    const nv = clampVersion(
      versions.length,
      msg.currentUserVersion ?? versions.length - 1,
      direction,
    );
    if (nv === null) return null;
    return versionRunIds?.[nv] ?? null;
  },

  // 模型消息答案分页（重新生成分支，与用户消息 1:N）：计算目标 runId。
  resolveAnswerVersionTarget: (msgId, direction) => {
    const msg = get().messages.find((m) => m.id === msgId);
    if (!msg) return null;
    const versions = msg.answerVersions;
    const runIds = msg.answerRunIds;
    if (!versions || !runIds || versions.length < 2) return null;
    const nv = clampVersion(
      versions.length,
      msg.currentAnswerVersion ?? versions.length - 1,
      direction,
    );
    if (nv === null) return null;
    return runIds[nv] ?? null;
  },

  setThumbsFeedback: (msgId, value) => {
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === msgId ? { ...m, thumbsFeedback: value } : m,
      ),
    }));
  },
}));

export {
  submitRequirement,
  editMessage,
  editAndRegenerate,
  regenerateMessage,
  retry,
  continueGeneration,
} from './chatActions';
