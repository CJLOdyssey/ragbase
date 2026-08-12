import type { listKeys } from '../api/client';
import type { ChatMessage } from '../types';

type KeyItem = Awaited<ReturnType<typeof listKeys>>[number];

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
