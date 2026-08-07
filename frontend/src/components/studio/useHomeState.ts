import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../auth';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { ChatMessage, ProjectRun, SessionItem } from '../../types';
import type { ModelOption } from '../../types/input';
import type { Conversation, Message } from '../../types/studio';
import { listModels } from '../../api/client/models';
import {
  deleteSession,
  getSessionDetail,
  listSessions,
  pinSession,
  renameSession,
} from '../../api/client/sessions';
import { submitRequirement } from '../../stores/chatActions';
import { useChatStore } from '../../stores/chatStore';
import Logger from '../../utils/logger';
import { useSettings } from '../../contexts/SettingsContext';

const MODEL_STORAGE_KEY = 'ragbase-selected-model';
const MODEL_CHANGED_EVENT = 'ragbase-model-changed';

function readStoredModel(): string {
  try {
    return localStorage.getItem(MODEL_STORAGE_KEY) || '';
  } catch {
    return '';
  }
}

function toConversation(s: SessionItem): Conversation {
  return {
    id: s.id,
    title: s.title,
    createdAt: s.created_at || '',
    updatedAt: s.updated_at || '',
    messages: [],
    isPinned: s.is_pinned ?? false,
  };
}

// 分支树：按 parent_run_id 组树，返回最新 run 的父链路径（根在前）
function buildRunPath(runs: ProjectRun[]): {
  path: ProjectRun[];
  active: string | null;
} {
  const byId = new Map(runs.map((r) => [r.id, r]));
  const latest = runs.reduce(
    (a, b) =>
      (b.created_at ?? '').localeCompare(a.created_at ?? '') > 0 ? b : a,
    runs[0],
  );
  const path: ProjectRun[] = [];
  const seen = new Set<string>();
  let cur: ProjectRun | undefined = latest;
  while (cur && !seen.has(cur.id)) {
    seen.add(cur.id);
    path.unshift(cur);
    cur = cur.parent_run_id ? byId.get(cur.parent_run_id) : undefined;
  }
  return { path, active: latest?.id ?? null };
}

export function useHomeState() {
  const { t } = useTranslation();
  const { settings, updateSettings } = useSettings();
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const messages = useChatStore((s) => s.messages);
  const isRunning = useChatStore((s) => s.status === 'running');
  const cancelRun = useChatStore((s) => s.cancelRun);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isApiOpen, setIsApiOpen] = useState(false);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState(readStoredModel);

  useEffect(() => {
    const sync = () => setSelectedModel(readStoredModel());
    window.addEventListener(MODEL_CHANGED_EVENT, sync);
    return () => window.removeEventListener(MODEL_CHANGED_EVENT, sync);
  }, []);

  const { data: sessions = [] } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => listSessions(),
    // Sessions are user-owned: only fetch once authentication is ready, and
    // re-fetch when it flips (login/refresh completes after initial mount).
    enabled: isAuthenticated,
  });

  const { data: models = [] } = useQuery({
    queryKey: ['models'],
    queryFn: async (): Promise<ModelOption[]> => {
      const infos = await listModels();
      return infos.map((m) => ({
        id: m.id,
        label: m.label,
        provider: m.provider,
      }));
    },
  });

  const [localTweaks, setLocalTweaks] = useState<
    Record<string, { title?: string; isPinned?: boolean }>
  >({});
  const [deletedIds, setDeletedIds] = useState<Set<string>>(new Set());

  const conversations: Conversation[] = useMemo(() => {
    return sessions
      .map(toConversation)
      .filter((c) => !deletedIds.has(c.id))
      .map((c) => {
        const tweak = localTweaks[c.id];
        return tweak
          ? {
              ...c,
              ...(tweak.title !== undefined ? { title: tweak.title } : {}),
              ...(tweak.isPinned !== undefined
                ? { isPinned: tweak.isPinned }
                : {}),
            }
          : c;
      });
  }, [sessions, localTweaks, deletedIds]);

  const displayMessages: Message[] = useMemo(
    () =>
      messages.map((m) => ({
        id: m.id,
        role: m.role === 'user' ? 'user' : 'agent',
        content: m.content,
        thinking: m.thinking,
        answer: m.content,
        thinkingDone: m.thinkingDone,
        userVersions: m.userVersions,
        currentUserVersion: m.currentUserVersion,
      })),
    [messages],
  );

  const hasMessages = displayMessages.length > 0;
  const effectiveModel = selectedModel || models[0]?.id || '';

  const handleSend = useCallback(
    async (text: string) => {
      if (!text.trim()) return;
      await submitRequirement(text);
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
    [queryClient],
  );

  const handleModelChange = useCallback((id: string) => {
    setSelectedModel(id);
    try {
      localStorage.setItem(MODEL_STORAGE_KEY, id);
    } catch {
      // storage unavailable — in-memory selection still applies
    }
    window.dispatchEvent(new Event(MODEL_CHANGED_EVENT));
  }, []);

  const handleSelectConversation = useCallback(
    async (convId: string | null) => {
      setActiveConvId(convId);
      if (!convId) return;
      try {
        const detail = await getSessionDetail(convId);
        const { path, active } = buildRunPath(detail.runs ?? []);

        const loaded: ChatMessage[] = [];
        for (const run of path) {
          for (const m of run.messages ?? []) {
            loaded.push({ ...m, runId: run.id });
          }
          // 版本计数：user 消息带 requirement_versions（run 层）
          const uIdx = loaded.findIndex(
            (m) => m.runId === run.id && m.role === 'user',
          );
          if (uIdx >= 0 && run.requirement_versions?.length) {
            loaded[uIdx] = {
              ...loaded[uIdx],
              userVersions: run.requirement_versions,
              currentUserVersion: run.requirement_versions.length - 1,
            };
          }
        }
        // Persisted messages are completed turns — mark agent thinking as done
        // so the ThinkingSection shows "已思考" instead of a stuck spinner.
        for (const m of loaded) {
          if (m.role !== 'user' && m.thinkingDone === undefined) {
            m.thinkingDone = true;
          }
        }
        useChatStore.getState().loadConversation(loaded, convId, convId);
        useChatStore.getState().setActiveRunId(active);
      } catch (err) {
        Logger.warn('[useHomeState] failed to load conversation', err);
      }
    },
    [],
  );

  const handleNewChat = useCallback(() => {
    useChatStore.getState().reset();
    setActiveConvId(null);
  }, []);

  const handleDeleteConversation = useCallback(
    (convId: string) => {
      if (activeConvId === convId) {
        useChatStore.getState().reset();
        setActiveConvId(null);
      }
      setDeletedIds((prev) => new Set(prev).add(convId));
      deleteSession(convId).catch((err) => {
        Logger.warn(
          '[useHomeState] failed to delete session %s: %s',
          convId,
          String(err),
        );
      });
    },
    [activeConvId],
  );

  const handleRenameConversation = useCallback(
    (convId: string, title: string) => {
      const trimmed = title.trim();
      if (!trimmed) return;
      setLocalTweaks((prev) => ({
        ...prev,
        [convId]: { ...prev[convId], title: trimmed },
      }));
      renameSession(convId, trimmed).catch((err) => {
        Logger.warn(
          '[useHomeState] failed to rename session %s: %s',
          convId,
          String(err),
        );
      });
    },
    [],
  );

  const handlePinConversation = useCallback(
    (convId: string) => {
      const current = conversations.find((c) => c.id === convId);
      const next = !current?.isPinned;
      setLocalTweaks((prev) => ({
        ...prev,
        [convId]: { ...prev[convId], isPinned: next },
      }));
      pinSession(convId, next).catch((err) => {
        Logger.warn(
          '[useHomeState] failed to pin session %s: %s',
          convId,
          String(err),
        );
      });
    },
    [conversations],
  );

  return {
    t,
    settings,
    updateSettings,
    isDarkMode: settings.theme === 'dark',
    conversations,
    activeConvId,
    setActiveConvId: handleSelectConversation,
    displayMessages,
    hasMessages,
    models,
    selectedModel: effectiveModel,
    setSelectedModel: handleModelChange,
    handleSend,
    handleStop: cancelRun,
    handleNewChat,
    handleDeleteConversation,
    handleRenameConversation,
    handlePinConversation,
    isSidebarOpen,
    setIsSidebarOpen,
    isUserMenuOpen,
    setIsUserMenuOpen,
    isSettingsOpen,
    setIsSettingsOpen,
    isApiOpen,
    setIsApiOpen,
    isRunning,
  };
}
