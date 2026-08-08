import { cancelRun as cancelRunApi } from '../api/client';
import { disconnectRun } from '../api/websocket';
import type { AppStatus, ChatMessage, RunResult } from '../types';
import Logger from '../utils/logger';
import { create } from 'zustand';
import type { ChatState } from './chatTypes';
import { uid } from './uid';

export type { WsConnectionStatus, ChatState } from './chatTypes';

const INITIAL_STATE = {
  currentRunId: null,
  activeRunId: null,
  runTurns: {},
  currentSessionId: null,
  currentConvId: null,
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

  loadConversation: (
    messages: ChatMessage[],
    convId?: string | null,
    sessionId?: string | null,
  ) => {
    const s = get();
    const prevRunId = s.currentRunId;
    if (prevRunId) {
      Logger.info(
        '[chat] loadConversation — disconnecting previous run %s',
        prevRunId,
      );
      disconnectRun(prevRunId);
    }
    set({
      messages,
      runTurns: {},
      currentConvId: convId ?? null,
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
    if (s.currentRunId) disconnectRun(s.currentRunId);
    set({ ...INITIAL_STATE, submissionConvId: null });
  },

  switchUserVersion: (msgId, direction) => {
    set((s) => ({
      messages: s.messages.map((m) => {
        if (m.id !== msgId || !m.userVersions) return m;
        const max = m.userVersions.length - 1;
        const cv = m.currentUserVersion ?? max;
        const nv =
          direction === 'prev' ? Math.max(0, cv - 1) : Math.min(max, cv + 1);
        return { ...m, currentUserVersion: nv, content: m.userVersions[nv] };
      }),
    }));
  },

  setThumbsFeedback: (msgId, value) => {
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === msgId ? { ...m, thumbs: value } : m,
      ),
    }));
  },

  setRunTurns: (turns) => set({ runTurns: turns }),
}));

export {
  submitRequirement,
  editMessage,
  editAndRegenerate,
  regenerateMessage,
  retry,
  continueGeneration,
} from './chatActions';
