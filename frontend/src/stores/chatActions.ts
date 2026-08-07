import {
  listKeys,
  resumeRun,
  submitRequirement as submitRequirementExternal,
} from '../api/client';
import { connectRun, disconnectRun } from '../api/websocket';
import type { ChatMessage } from '../types';
import Logger from '../utils/logger';
import { useChatStore } from './chatStore';
import { createStreamHandler } from './chatStreaming';
import { uid } from './uid';

type KeyItem = Awaited<ReturnType<typeof listKeys>>[number];

function resolveKey(
  activeKeys: KeyItem[],
  persistedModel: string | undefined,
): { keyId?: string; model?: string } {
  // Route to the key whose models contain the model the user actually selected in the UI,
  // so a SiliconFlow/Groq model is never sent to a DeepSeek base URL.
  const owningKey = persistedModel
    ? activeKeys.find((k) => k.models.includes(persistedModel))
    : undefined;
  if (owningKey) {
    return { keyId: owningKey.id, model: persistedModel ?? undefined };
  }
  const defaultKey =
    activeKeys.find((k) => k.is_default && k.is_active) || activeKeys[0];
  if (defaultKey) {
    return {
      keyId: defaultKey.id,
      model:
        persistedModel && defaultKey.models.includes(persistedModel)
          ? persistedModel
          : defaultKey.models[0],
    };
  }
  return {};
}

export async function submitRequirement(
  requirement: string,
  session_id?: string,
  skipAddUserMessage?: boolean,
  submissionConvId?: string | null,
  parent_run_id?: string,
) {
  const s = useChatStore.getState();
  const effectiveSessionId = session_id || s.currentSessionId || undefined;
  if (s.currentRunId) {
    disconnectRun(s.currentRunId);
  }
  useChatStore.setState({ submissionConvId: submissionConvId ?? null });

  let keyId: string | undefined;
  let model: string | undefined;
  try {
    const keys = await listKeys();
    const activeKeys = keys.filter((k) => k.is_active);
    const persistedModel = localStorage.getItem('ragbase-selected-model');
    const resolved = resolveKey(activeKeys, persistedModel ?? undefined);
    keyId = resolved.keyId;
    model = resolved.model;
  } catch {
    // Key vault unavailable
  }

  if (!keyId) {
    useChatStore.setState({
      status: 'error',
      error: '请先在设置中配置 API Key',
      wsStatus: 'disconnected',
    });
    return;
  }

  const userMsg: ChatMessage = {
    id: uid(),
    role: 'user',
    agent_name: '我',
    content: requirement,
    round_number: 0,
    created_at: new Date().toISOString(),
  };

  useChatStore.setState({
    status: 'loading',
    error: null,
    result: null,
    messages: skipAddUserMessage
      ? useChatStore.getState().messages
      : [...useChatStore.getState().messages, userMsg],
    currentRole: null,
  });

  try {
    Logger.info('[chat] submitRequirement — session_id=%s', effectiveSessionId);
    const resp = await submitRequirementExternal(
      requirement,
      effectiveSessionId,
      keyId,
      model,
      parent_run_id,
    );
    const run_id = resp.run_id;
    const returnedSessionId = resp.session_id || effectiveSessionId || null;
    useChatStore.setState({
      currentRunId: run_id,
      activeRunId: run_id,
      currentSessionId: returnedSessionId,
      status: 'running',
      wsStatus: 'connecting',
    });
    // Bind the freshly-added user message to its run so edit-regenerate can
    // resolve the parent_run_id from "run-{run_id}-requirement" on a later edit.
    if (!skipAddUserMessage) {
      useChatStore.setState((prev) => {
        const msgs = [...prev.messages];
        const last = msgs[msgs.length - 1];
        if (last && last.role === 'user' && !last.id.startsWith('run-')) {
          msgs[msgs.length - 1] = { ...last, id: `run-${run_id}-requirement` };
        }
        return { messages: msgs };
      });
    } else {
      // Edit-regenerate: rebind the EDITED user message to the new run, or the
      // next edit resolves parent_run_id to the stale first run and the backend
      // requirement_versions chain silently drops intermediate versions.
      useChatStore.setState((prev) => {
        const msgs = [...prev.messages];
        const targetIdx = msgs.findIndex((m) => m.id === prev.editTargetId);
        const userIdx = targetIdx > 0 ? targetIdx - 1 : -1;
        const u =
          userIdx >= 0 && msgs[userIdx].role === 'user' ? msgs[userIdx] : null;
        if (u && u.id.startsWith('run-') && u.id.endsWith('-requirement')) {
          msgs[userIdx] = { ...u, id: `run-${run_id}-requirement` };
        }
        return { messages: msgs };
      });
    }
    connectRun(run_id, {
      onMessage: createStreamHandler(
        useChatStore.setState,
        useChatStore.getState,
      ),
    });
  } catch (err: unknown) {
    Logger.error('[chat] submitRequirement failed:', err);
    const errMsg = err instanceof Error ? err.message : String(err);
    useChatStore.setState({ status: 'error', error: errMsg });
  }
}

export function editMessage(msgIndex: number, newContent: string) {
  useChatStore.setState((s) => {
    const updated = [...s.messages];
    const msg = { ...updated[msgIndex], content: newContent };
    updated[msgIndex] = msg;
    return { messages: updated };
  });
}

export async function regenerateMessage(msgIndex: number) {
  const s = useChatStore.getState();
  Logger.info('[chat] regenerateMessage — from index %d', msgIndex);
  if (msgIndex < 1) return;
  const userMsg = s.messages[msgIndex - 1];
  if (!userMsg) return;
  if (s.currentRunId) disconnectRun(s.currentRunId);

  // The synthetic user message id is "run-{run_id}-requirement" — parse the run
  // this regeneration replaces so the backend links the edit chain
  // (parent_run_id); merge_edit_chains then folds the old answer into versions
  // instead of leaving an orphan run (stale reply + duplicated user message).
  let parentRunId: string | undefined;
  if (userMsg.id?.startsWith('run-') && userMsg.id.endsWith('-requirement')) {
    parentRunId = userMsg.id.slice(4, -'-requirement'.length);
  }

  useChatStore.setState({
    status: 'loading',
    error: null,
    result: null,
    messages: s.messages.slice(0, msgIndex),
  });
  await submitRequirement(
    userMsg.content,
    s.currentSessionId ?? undefined,
    true,
    null,
    parentRunId,
  );
}

/**
 * Edit a user message and regenerate the following answer.
 *
 * Semantics (edit → model rethinks, old answers kept as versions):
 *  - The user message keeps its edit history in `userVersions` (content becomes the new edit).
 *  - The first agent answer after the edited message becomes the merge target: the streamed
 *    new answer is appended to that message's `versions` instead of inserting a new message,
 *    so older answers are never deleted and can be browsed with the pagination arrows.
 */
export async function editAndRegenerate(userMsgId: string, newContent: string) {
  const s = useChatStore.getState();
  const idx = s.messages.findIndex((m) => m.id === userMsgId);
  if (idx < 0) return;
  const old = s.messages[idx];
  const trimmed = newContent.trim();
  if (!trimmed || old.content === trimmed) return;
  if (s.currentRunId) disconnectRun(s.currentRunId);

  // The synthetic user message id is "run-{run_id}-requirement" — parse the run
  // this edit replaces so the backend can link the edit chain (parent_run_id).
  let parentRunId: string | undefined;
  if (old.id && old.id.startsWith('run-') && old.id.endsWith('-requirement')) {
    parentRunId = old.id.slice(4, -'-requirement'.length);
  }

  // First non-user message after the edit is the merge target.
  const nextAgentIdx = s.messages.findIndex(
    (m, i) => i > idx && m.role !== 'user',
  );
  const editTargetId = nextAgentIdx >= 0 ? s.messages[nextAgentIdx].id : null;

  useChatStore.setState({
    status: 'loading',
    error: null,
    result: null,
    streamingId: null,
    continuingId: null,
    editTargetId,
    pendingVersions: null,
    pendingThinkingVersions: null,
    skipThinking: false,
    messages: s.messages.map((m, i) =>
      i === idx ? { ...m, content: trimmed } : m,
    ),
  });

  await submitRequirement(
    trimmed,
    s.currentSessionId ?? undefined,
    true,
    null,
    parentRunId,
  );
}

export async function retry() {
  const s = useChatStore.getState();
  Logger.info('[chat] retry — re-submitting last user message');
  useChatStore.setState({ status: 'loading', error: null, result: null });
  if (s.currentRunId) {
    disconnectRun(s.currentRunId);
  }
  const lastUserMsg = [...s.messages].reverse().find((m) => m.role === 'user');
  if (!lastUserMsg) {
    useChatStore.setState({
      status: 'error',
      error: '没有找到用户消息，无法重试',
    });
    return;
  }
  useChatStore.setState({ currentRunId: null });
  try {
    const resp = await submitRequirementExternal(
      lastUserMsg.content,
      s.currentSessionId ?? undefined,
    );
    useChatStore.setState({
      currentRunId: resp.run_id,
      currentSessionId: resp.session_id || s.currentSessionId || null,
      status: 'running',
      wsStatus: 'connecting',
    });
    connectRun(resp.run_id, {
      onMessage: createStreamHandler(
        useChatStore.setState,
        useChatStore.getState,
      ),
    });
  } catch (err: unknown) {
    Logger.error('[chat] retry failed:', err);
    const errMsg = err instanceof Error ? err.message : String(err);
    useChatStore.setState({ status: 'error', error: errMsg });
  }
}

export async function continueGeneration() {
  const s = useChatStore.getState();
  const intId = s.interruptedMessageId;
  if (!intId) return;
  const idx = s.messages.findIndex((m) => m.id === intId);
  if (idx < 0) {
    useChatStore.setState({ interruptedMessageId: null });
    return;
  }
  Logger.info(
    '[chat] continueGeneration — continuing from interrupted msg %s',
    intId,
  );
  const interruptedMsg = s.messages[idx];
  useChatStore.setState({
    continuingId: intId,
    skipThinking: false,
    pendingVersions: null,
    pendingThinkingVersions: null,
  });
  const continuation = interruptedMsg.content;
  const prevRunId = s.currentRunId;
  if (prevRunId) disconnectRun(prevRunId);
  useChatStore.setState({ status: 'loading', error: null, result: null });
  try {
    const resp = await resumeRun(
      continuation,
      s.currentSessionId || undefined,
      interruptedMsg.thinking,
    );
    const run_id = resp.run_id;
    const returnedSessionId = resp.session_id || s.currentSessionId || null;
    useChatStore.setState({
      currentRunId: run_id,
      currentSessionId: returnedSessionId,
      status: 'running',
      wsStatus: 'connecting',
    });
    connectRun(run_id, {
      onMessage: createStreamHandler(
        useChatStore.setState,
        useChatStore.getState,
      ),
    });
  } catch (err: unknown) {
    Logger.error('[chat] continueGeneration failed:', err);
    const errMsg = err instanceof Error ? err.message : String(err);
    useChatStore.setState({ status: 'error', error: errMsg });
  }
}
