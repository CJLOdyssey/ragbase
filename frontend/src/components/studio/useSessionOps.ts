import {
  useCallback,
  useMemo,
  useState,
  type Dispatch,
  type SetStateAction,
} from 'react';
import { useNavigate } from 'react-router-dom';
import type { SessionItem } from '../../types';
import type { Conversation } from '../../types/studio';
import {
  deleteSession,
  pinSession,
  renameSession,
} from '../../api/client/sessions';
import {
  persistActiveConvId,
  toConversation,
  writeSessionsCache,
} from '../../stores/sessionCache';
import Logger from '../../utils/logger';

interface SessionOpsParams {
  cachedSessions: SessionItem[];
  setCachedSessions: Dispatch<SetStateAction<SessionItem[]>>;
  activeConvId: string | null;
  setRestoring: (restoring: boolean) => void;
}

// 会话列表增删改（本地乐观 tweak + 后端同步）。localTweaks/deletedIds 是
// 仅前端生效的轻量覆盖（重命名/置顶/删除），刷新后以后端数据为准。
export function useSessionOps({
  cachedSessions,
  setCachedSessions,
  activeConvId,
  setRestoring,
}: SessionOpsParams) {
  const navigate = useNavigate();
  const [localTweaks, setLocalTweaks] = useState<
    Record<string, { title?: string; isPinned?: boolean }>
  >({});
  const [deletedIds, setDeletedIds] = useState<Set<string>>(new Set());

  const conversations: Conversation[] = useMemo(() => {
    return cachedSessions
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
  }, [cachedSessions, localTweaks, deletedIds]);

  const handleSelectConversation = useCallback(
    (convId: string | null) => {
      persistActiveConvId(convId);
      navigate(convId ? `/chat/${convId}` : '/');
    },
    [navigate],
  );

  const handleNewChat = useCallback(() => {
    persistActiveConvId(null);
    setRestoring(false);
    navigate('/');
  }, [navigate, setRestoring]);

  const handleDeleteConversation = useCallback(
    (convId: string) => {
      if (activeConvId === convId) {
        persistActiveConvId(null);
        setRestoring(false);
        navigate('/');
      }
      setDeletedIds((prev) => new Set(prev).add(convId));
      setCachedSessions((prev) => {
        const next = prev.filter((c) => c.id !== convId);
        writeSessionsCache(next);
        return next;
      });
      deleteSession(convId).catch((err) => {
        Logger.warn(
          '[useHomeState] failed to delete session %s: %s',
          convId,
          String(err),
        );
      });
    },
    [activeConvId, navigate, setCachedSessions, setRestoring],
  );

  const handleRenameConversation = useCallback(
    (convId: string, title: string) => {
      const trimmed = title.trim();
      if (!trimmed) return;
      setLocalTweaks((prev) => ({
        ...prev,
        [convId]: { ...prev[convId], title: trimmed },
      }));
      setCachedSessions((prev) => {
        const next = prev.map((c) =>
          c.id === convId ? { ...c, title: trimmed } : c,
        );
        writeSessionsCache(next);
        return next;
      });
      renameSession(convId, trimmed).catch((err) => {
        Logger.warn(
          '[useHomeState] failed to rename session %s: %s',
          convId,
          String(err),
        );
      });
    },
    [setCachedSessions],
  );

  const handlePinConversation = useCallback(
    (convId: string) => {
      const current = conversations.find((c) => c.id === convId);
      const next = !current?.isPinned;
      setLocalTweaks((prev) => ({
        ...prev,
        [convId]: { ...prev[convId], isPinned: next },
      }));
      setCachedSessions((prev) => {
        const updated = prev.map((c) =>
          c.id === convId ? { ...c, is_pinned: next } : c,
        );
        writeSessionsCache(updated);
        return updated;
      });
      pinSession(convId, next).catch((err) => {
        Logger.warn(
          '[useHomeState] failed to pin session %s: %s',
          convId,
          String(err),
        );
      });
    },
    [conversations, setCachedSessions],
  );

  return {
    conversations,
    handleSelectConversation,
    handleNewChat,
    handleDeleteConversation,
    handleRenameConversation,
    handlePinConversation,
  };
}
