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
  listSessions,
  pinSession,
  renameSession,
} from '../../api/client/sessions';
import {
  persistActiveConvId,
  toConversation,
  writeSessionsCache,
} from '../../stores/sessionCache';
import { mergeSessions } from '../../stores/sessionMerge';
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

  // 乐观更新失败时以 server 为准纠正本地列表（回滚 tweak/deletedIds 的残留）。
  const refetchSessions = useCallback(() => {
    listSessions(100)
      .then((data) => {
        // 唯一化归并：保留发送中的乐观占位（temp）
        setCachedSessions((prev) => {
          const merged = mergeSessions(prev, data);
          writeSessionsCache(merged);
          return merged;
        });
      })
      .catch(() => {
        // non-fatal
      });
  }, [setCachedSessions]);

  const dropTweak = useCallback((convId: string) => {
    setLocalTweaks((prev) => {
      if (!(convId in prev)) return prev;
      const next = { ...prev };
      delete next[convId];
      return next;
    });
  }, []);

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
      // 乐观占位（temp-*）无 server 会话，仅本地删除
      if (convId.startsWith('temp-')) return;
      deleteSession(convId).catch((err) => {
        Logger.warn(
          '[useHomeState] failed to delete session %s: %s',
          convId,
          String(err),
        );
        // 乐观删除失败 → 撤销 deletedIds 并以 server 为准恢复列表
        setDeletedIds((prev) => {
          if (!prev.has(convId)) return prev;
          const next = new Set(prev);
          next.delete(convId);
          return next;
        });
        refetchSessions();
      });
    },
    [activeConvId, navigate, setCachedSessions, setRestoring, refetchSessions],
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
      // 乐观占位（temp-*）无 server 会话，仅本地更新
      if (convId.startsWith('temp-')) return;
      renameSession(convId, trimmed).catch((err) => {
        Logger.warn(
          '[useHomeState] failed to rename session %s: %s',
          convId,
          String(err),
        );
        // 乐观重命名失败 → 回滚 tweak 并以 server 为准纠正标题
        dropTweak(convId);
        refetchSessions();
      });
    },
    [setCachedSessions, dropTweak, refetchSessions],
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
      // 乐观占位（temp-*）无 server 会话，仅本地更新
      if (convId.startsWith('temp-')) return;
      pinSession(convId, next).catch((err) => {
        Logger.warn(
          '[useHomeState] failed to pin session %s: %s',
          convId,
          String(err),
        );
        // 乐观置顶失败 → 回滚 tweak 并以 server 为准纠正
        dropTweak(convId);
        refetchSessions();
      });
    },
    [conversations, setCachedSessions, dropTweak, refetchSessions],
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
