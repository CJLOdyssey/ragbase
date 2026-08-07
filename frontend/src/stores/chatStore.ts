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
      Logger.info('[chat] cancelRun — disconnecting run %s', prevRunId);
      disconnectRun(prevRunId);
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

  switchVersion: (msgId, direction) => {
    set((s) => ({
      messages: s.messages.map((m) => {
        if (m.id !== msgId || !m.versions) return m;
        const max = m.versions.length - 1;
        const cv = m.currentVersion ?? max;
        const nv =
          direction === 'prev' ? Math.max(0, cv - 1) : Math.min(max, cv + 1);
        return {
          ...m,
          currentVersion: nv,
          content: m.versions[nv],
          thinking: m.thinkingVersions?.[nv] ?? m.thinking ?? '',
        };
      }),
    }));
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

  setAgentVersion: (msgId, nv) => {
    set((s) => ({
      messages: s.messages.map((m) => {
        if (m.id !== msgId) return m;
        // nv === -1 means "show the live content" (the newest answer), which lives
        // in m.content rather than the folded versions list.
        if (nv === -1) {
          return {
            ...m,
            currentVersion: -1,
            content: m.content,
            thinking: m.thinking,
          };
        }
        const max = m.versions?.length ? m.versions.length - 1 : 0;
        const idx = Math.max(0, Math.min(nv, max));
        return {
          ...m,
          currentVersion: idx,
          // ponytail: never fall back to the live (newest) content/thinking here —
          // a missing historical version renders blank rather than showing the
          // newest answer against an older user message (version mismatch bug).
          content: m.versions?.[idx] ?? '',
          thinking: m.thinkingVersions?.[idx] ?? '',
        };
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
}));

export {
  submitRequirement,
  editMessage,
  editAndRegenerate,
  regenerateMessage,
  retry,
  continueGeneration,
} from './chatActions';
