import { listKeys } from '../api/client';
import { rewriteQuery } from '../api/client';
import type { ChatMessage } from '../types';
import Logger from '../utils/logger';

type KeyItem = Awaited<ReturnType<typeof listKeys>>[number];

export async function resolveKeyAndModel(): Promise<{
  keyId?: string;
  model?: string;
}> {
  try {
    const keys = await listKeys();
    const activeKeys = keys.filter((k) => k.is_active);
    const persistedModel = localStorage.getItem('ragbase-selected-model');
    return resolveKey(activeKeys, persistedModel ?? undefined);
  } catch {
    return {};
  }
}

export async function rewriteQueryWithContext(
  query: string,
  messages: readonly ChatMessage[],
  sessionId: string | undefined,
): Promise<string> {
  try {
    const historyMessages = messages.slice(-4).map((m) => ({
      role: m.role === 'user' ? 'user' : 'assistant',
      content: m.content,
    }));
    const resp = await rewriteQuery({
      query,
      history: historyMessages,
      session_id: sessionId,
    });
    const result = resp.rewritten_query || query;
    Logger.info('[chat] query rewritten: "%s" -> "%s"', query, result);
    return result;
  } catch (err) {
    Logger.warn('[chat] query rewrite failed, using original query:', err);
    return query;
  }
}

export function bindUserMessageToRun(
  runId: string,
  skipAddUserMessage: boolean,
  editTargetId: string | null | undefined,
) {
  return (prev: { messages: ChatMessage[] }) => {
    const msgs = [...prev.messages];
    if (!skipAddUserMessage) {
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'user' && !last.id.startsWith('run-')) {
        msgs[msgs.length - 1] = { ...last, id: `run-${runId}-requirement` };
      }
      return { messages: msgs };
    }
    const targetIdx = editTargetId
      ? msgs.findIndex((m) => m.id === editTargetId) - 1
      : msgs.length - 1;
    const u =
      targetIdx >= 0 && msgs[targetIdx]?.role === 'user'
        ? msgs[targetIdx]
        : null;
    if (!u) return { messages: msgs };
    const versionRunIds = u.versionRunIds
      ? [...u.versionRunIds, runId]
      : [runId];
    msgs[targetIdx] = {
      ...u,
      id: `run-${runId}-requirement`,
      runId,
      versionRunIds,
    };
    return { messages: msgs };
  };
}

export function buildEditVersions(
  old: ChatMessage,
  trimmed: string,
  editedRunId: string | null | undefined,
): { userVersions: string[]; baseRunIds: string[] } {
  // 本地版本链（乐观）：与新 run 的 requirement_versions 对应，驱动分页切换。
  const history = old.userVersions ? [...old.userVersions] : [];
  const userVersions =
    history.length === 0 || history[history.length - 1] !== old.content
      ? [...history, old.content, trimmed]
      : [...history, trimmed];
  // 版本 → runId：旧版本继承已加载的版本链；缺失时兜底为被编辑 turn 自身，
  // 使切回（←）能定位到被编辑 turn 所在分支，而非停在当前分支。
  const baseRunIds = old.versionRunIds
    ? [...old.versionRunIds]
    : editedRunId
      ? [editedRunId]
      : [];
  return { userVersions, baseRunIds };
}

export function resolveKey(
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
