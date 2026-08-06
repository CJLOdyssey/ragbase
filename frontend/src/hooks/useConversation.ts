import { useState, useCallback, useEffect } from 'react';
import type { Conversation } from '../types/AgentStudio';
import { useChatStore } from '../stores/chatStore';
import { listSessions, deleteSession } from '../api/client/sessions';
import Logger from '../utils/logger';

const uid = () => Date.now().toString(36) + Math.random().toString(36).substring(2, 10);
const ACTIVE_CONV_KEY = 'agentstudio-active-conv-id';

/**
 * Conversation list manager — tracks saved conversations in localStorage.
 *
 * This hook handles ONLY conversation metadata (title, timestamps, persisted message list).
 * Actual message state is managed by chatStore (Zustand) which is the single source of
 * truth for real-time API/WebSocket messages.
 *
 * Mock fallback responses have been removed — see utils/agentResponses.ts for the
 * legacy mock system which is now only used when no API agents are configured.
 */
export function useConversation() {
  const [activeConvId, setActiveConvId] = useState<string | null>(() => {
    try {
      return localStorage.getItem(ACTIVE_CONV_KEY);
    } catch {
      return null;
    }
  });
  const [conversations, setConversations] = useState<Conversation[]>(() => {
    try {
      const saved = localStorage.getItem('agentstudio-conversations');
      if (!saved) return [];
      const convs = JSON.parse(saved);

      let needsPersist = false;
      for (const conv of convs) {
        if (!conv.messages?.length || !conv.createdAt || !conv.updatedAt) continue;
        const start = new Date(conv.createdAt).getTime();
        const end = new Date(conv.updatedAt).getTime();
        if (isNaN(start) || isNaN(end) || start >= end) continue;
        const total = conv.messages.length;
        for (let i = 0; i < total; i++) {
          const m = conv.messages[i];
          if (m.timestamp || m.created_at) continue;
          const estimated = start + (end - start) * ((i + 0.5) / total);
          m.created_at = new Date(estimated).toISOString();
          needsPersist = true;
        }
        const msgTimes = conv.messages
          .map((m: { created_at?: string }) => (m.created_at ? new Date(m.created_at).getTime() : null))
          .filter((t: number | null): t is number => t !== null);
        if (msgTimes.length > 0) {
          const lastMsgTime = Math.max(...msgTimes);
          const curUpdatedAt = new Date(conv.updatedAt).getTime();
          if (Math.abs(lastMsgTime - curUpdatedAt) > 3600000) {
            conv.updatedAt = new Date(lastMsgTime).toISOString();
            needsPersist = true;
          }
        }
      }

      if (needsPersist) {
        localStorage.setItem('agentstudio-conversations', JSON.stringify(convs));
      }

      return convs;
    } catch {
      return [];
    }
  });

  // Persist activeConvId across page refreshes
  useEffect(() => {
    try {
      if (activeConvId) {
        localStorage.setItem(ACTIVE_CONV_KEY, activeConvId);
      } else {
        localStorage.removeItem(ACTIVE_CONV_KEY);
      }
    } catch {
      // non-fatal
    }
  }, [activeConvId]);

  // Persist to localStorage whenever conversations change
  useEffect(() => {
    try {
      localStorage.setItem('agentstudio-conversations', JSON.stringify(conversations));
    } catch {
      // localStorage full or unavailable — non-fatal
    }
  }, [conversations]);

  // Listen for external writes (from chatStore sync)
  useEffect(() => {
    const handler = () => {
      try {
        const saved = localStorage.getItem('agentstudio-conversations');
        setConversations(saved ? JSON.parse(saved) : []);
      } catch { /* non-fatal */ }
    };
    window.addEventListener('agentstudio-conversations-updated', handler);
    return () => window.removeEventListener('agentstudio-conversations-updated', handler);
  }, []);

  useEffect(() => {
    const rt = localStorage.getItem('agentstudio_refresh_token');
    if (!rt) return;

    let cancelled = false;
    listSessions(100).then((sessions) => {
      if (cancelled) return;
      setConversations((prev) => {
        const localSessionIds = new Set(
          prev.map((c) => c.sessionId).filter(Boolean)
        );
        const apiConvs: Conversation[] = [];
        for (const s of sessions) {
          if (localSessionIds.has(s.id)) continue;
          apiConvs.push({
            id: crypto.randomUUID?.() || uid(),
            title: s.title,
            messages: [],
            kind: s.kind as 'normal' | 'agent' | 'team' || 'normal',
            agentId: s.agent_id || undefined,
            createdAt: s.created_at || new Date().toISOString(),
            updatedAt: s.updated_at || s.created_at || new Date().toISOString(),
            sessionId: s.id,
          });
        }
        if (apiConvs.length === 0) return prev;
        const merged = [...apiConvs, ...prev];
        localStorage.setItem('agentstudio-conversations', JSON.stringify(merged));
        return merged;
      });
    }).catch(() => {});
    return () => { cancelled = true; };
  }, []);

  /** Persist conversations to localStorage immediately (not just via the debounced effect). */
  const persistConversations = useCallback((convs: Conversation[]) => {
    try {
      localStorage.setItem('agentstudio-conversations', JSON.stringify(convs));
    } catch {
      // non-fatal
    }
  }, []);

  /** Save or update a conversation. If convId exists, updates it; otherwise creates new. */
  const saveConversation = useCallback((title: string, messages: unknown[], agentId?: string, teamId?: string, teamName?: string, kind?: 'normal' | 'agent' | 'team') => {
    const now = new Date().toISOString();
    const id = crypto.randomUUID?.() || uid();
    const conv: Conversation = {
      id,
      title: title.length > 36 ? title.slice(0, 36) + '...' : title,
      messages: messages as Conversation['messages'],
      createdAt: now,
      updatedAt: now,
      kind,
      agentId,
      teamId,
      teamName,
    };
    setConversations((prev) => {
      const next = [conv, ...prev];
      persistConversations(next);
      return next;
    });
    setActiveConvId(id);
    return id;
  }, [persistConversations]);

  /** Update messages for an existing conversation. */
  const updateConversationMessages = useCallback((convId: string, messages: unknown[], updateTimestamps = true, teamId?: string, teamName?: string) => {
    setConversations((prev) => {
      const next = prev.map((c) =>
        c.id === convId
          ? { ...c, messages: messages as Conversation['messages'], ...(updateTimestamps ? { updatedAt: new Date().toISOString() } : {}), ...(teamId !== undefined ? { teamId } : {}), ...(teamName !== undefined ? { teamName } : {}) }
          : c,
      );
      persistConversations(next);
      return next;
    });
  }, [persistConversations]);

  /** Update session ID for an existing conversation (links to backend session). */
  const updateConversationSessionId = useCallback((convId: string, sessionId: string, updateTimestamps = true) => {
    setConversations((prev) => {
      const next = prev.map((c) =>
        c.id === convId ? { ...c, sessionId, ...(updateTimestamps ? { updatedAt: new Date().toISOString() } : {}) } : c,
      );
      persistConversations(next);
      return next;
    });
  }, [persistConversations]);

  /** Delete a conversation by ID — removes the local record AND the server session. */
  const deleteConversation = useCallback((convId: string) => {
    const conv = conversations.find((c) => c.id === convId);
    setConversations((prev) => {
      const next = prev.filter((c) => c.id !== convId);
      persistConversations(next);
      return next;
    });
    setActiveConvId((current) => {
      if (current === convId) {
        useChatStore.getState().reset();
        return null;
      }
      return current;
    });
    if (conv?.sessionId) {
      deleteSession(conv.sessionId).catch((err) => {
        Logger.warn('[conversation] failed to delete server session %s: %s', conv.sessionId, String(err));
      });
    }
  }, [conversations, persistConversations]);

  return {
    activeConvId,
    setActiveConvId,
    conversations,
    setConversations,
    saveConversation,
    updateConversationMessages,
    updateConversationSessionId,
    deleteConversation,
  };
}
