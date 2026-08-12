import {
  listKeys,
  resumeRun,
  submitRequirement as submitRequirementExternal,
} from '../api/client';
import { connectRun, disconnectRun } from '../api/websocket';
import i18n from '../i18n';
import type { AttachmentInfo, ChatMessage } from '../types';
import Logger from '../utils/logger';
import { useChatStore } from './chatStore';
import { createStreamHandler } from './chatStreaming';
import { invalidateSessionCache } from './sessionCache';
import { uid } from './uid';

type KeyItem = Awaited<ReturnType<typeof listKeys>>[number];

function buildEditVersions(
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
  parent_run_id?: string | null,
  attachment_ids?: string[],
  attachmentInfo?: AttachmentInfo[],
) {
  const s = useChatStore.getState();
  const effectiveSessionId = session_id || s.currentSessionId || undefined;
  // 新生成改变会话内容 — 失效该会话的消息缓存（SWR 一致性）。
  invalidateSessionCache(effectiveSessionId);
  // 显式传 parent_run_id（编辑分支，含 null=根）时按传入值；未传（正常续聊）
  // 才回退到 activeRunId。
  const effectiveParentRunId =
    parent_run_id === undefined ? s.activeRunId : parent_run_id;
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
      error: i18n.t('chat.configureKeyFirst'),
      wsStatus: 'disconnected',
    });
    return;
  }

  const userMsg: ChatMessage = {
    id: uid(),
    role: 'user',
    agent_name: i18n.t('chat.me'),
    content: requirement,
    round_number: 0,
    created_at: new Date().toISOString(),
    // 携带本 run 的 parent（流式生成时也记录，编辑时用于产生兄弟分支；
    // 若缺失会回退到 activeRunId，导致编辑根 turn 误成续写）
    parentRunId: effectiveParentRunId,
    // 乐观 user 消息直接展示附件（刷新后由 buildPathTurns 从 run 恢复）
    attachments: attachmentInfo,
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
      effectiveParentRunId,
      attachment_ids,
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
      // Edit-regenerate / regenerate: rebind the target user message to the new
      // run, or the next edit resolves parent_run_id to a stale run and the
      // backend requirement_versions chain silently drops intermediate versions.
      useChatStore.setState((prev) => {
        const msgs = [...prev.messages];
        // edit 场景：editTargetId 前一条用户消息；regenerate 场景：截断后最后一条。
        const targetIdx = prev.editTargetId
          ? msgs.findIndex((m) => m.id === prev.editTargetId) - 1
          : msgs.length - 1;
        const u =
          targetIdx >= 0 && msgs[targetIdx]?.role === 'user'
            ? msgs[targetIdx]
            : null;
        if (!u) return { messages: msgs };
        // 版本链最后一跳 = 新 run。userVersions/currentUserVersion 不在此写：
        // 用户消息版本器由加载时 attachBranchVersions 全量挂载（branchGroup），
        // 流式路径只维护 run 映射（versionRunIds）。
        const versionRunIds = u.versionRunIds
          ? [...u.versionRunIds, run_id]
          : [run_id];
        msgs[targetIdx] = {
          ...u,
          id: `run-${run_id}-requirement`,
          runId: run_id,
          versionRunIds,
        };
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

  // 重新生成 = 重新回答该用户问题，产生兄弟分支：新 run 的 parent = 被重
  // 生成 turn 的 parent（与编辑一致），而非 turn 自身。parentRunId 在加载
  // （buildPathTurns）与流式提交（submitRequirement）时都注入，刷新后仍可靠；
  // 不能用 synthetic id "run-{id}-requirement"（仅流式会话存在，刷新后消失）。
  const parentRunId = userMsg.parentRunId ?? null;
  // 被重新生成 turn 的旧 run：优先接续已有答案分页列表（多次重新生成累积），
  // 否则用消息 runId（流式消息带 runId，加载消息经 buildPathTurns 注入）。
  const modelMsg = s.messages[msgIndex];
  const oldRunIds =
    modelMsg?.answerRunIds && modelMsg.answerRunIds.length > 0
      ? modelMsg.answerRunIds
      : modelMsg?.runId
        ? [modelMsg.runId]
        : [];

  useChatStore.setState({
    status: 'loading',
    error: null,
    result: null,
    streamingId: null,
    skipThinking: false,
    messages: s.messages.slice(0, msgIndex),
    pendingRegenerate: {
      userMsgId: userMsg.id,
      oldRunIds,
      requirement: userMsg.content,
    },
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

  // The edited user message carries its run's parent_run_id (set at load time).
  // Editing branches a sibling: the new run's parent is the edited turn's parent,
  // so the result sits alongside (not as a continuation of) the edited turn.
  // null = edited a root turn → new run is a fresh root (parent explicitly null).
  const parentRunId = old.parentRunId ?? null;

  // The run this edit replaces (for version navigation back to it). Prefer the
  // synthetic id "run-{runId}-requirement", fall back to the stored runId.
  const editedRunId =
    old.id && old.id.startsWith('run-') && old.id.endsWith('-requirement')
      ? old.id.slice(4, -'-requirement'.length)
      : (old.runId ?? null);

  // First non-user message after the edit is the merge target.
  const nextAgentIdx = s.messages.findIndex(
    (m, i) => i > idx && m.role !== 'user',
  );
  const editTargetId = nextAgentIdx >= 0 ? s.messages[nextAgentIdx].id : null;

  const { userVersions, baseRunIds } = buildEditVersions(
    old,
    trimmed,
    editedRunId,
  );

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
    // 分支语义：编辑 = 切到新分支，分支点之后的轮次（后续 turn）从视图
    // 截断隐藏（DB 留存），只保留本 turn 供流式替换。
    messages: s.messages
      .slice(0, nextAgentIdx >= 0 ? nextAgentIdx + 1 : s.messages.length)
      .map((m, i) =>
        i === idx
          ? {
              ...m,
              content: trimmed,
              userVersions,
              versionRunIds: baseRunIds,
              currentUserVersion: userVersions.length - 1,
            }
          : m,
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
      error: i18n.t('chat.noUserMessage'),
    });
    return;
  }
  useChatStore.setState({ currentRunId: null });
  // 重试与正常发送走同一 key/model 解析（否则落到后端 config 默认模型，
  // 硅基流动/免费模型会被错误路由到 deepseek 默认 key）。
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
    // Key vault unavailable — backend falls back to the default model
  }
  if (!keyId) {
    useChatStore.setState({
      status: 'error',
      error: i18n.t('chat.configureKeyFirst'),
      wsStatus: 'disconnected',
    });
    return;
  }
  try {
    const resp = await submitRequirementExternal(
      lastUserMsg.content,
      s.currentSessionId ?? undefined,
      keyId,
      model,
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
  const continuation = interruptedMsg.content;
  if (!continuation.trim() && !interruptedMsg.thinking?.trim()) {
    // 思考与正文都未生成：没有可续写的原料（思考链也可作续写原料）。
    Logger.warn(
      '[chat] continueGeneration — interrupted msg %s has no content/thinking, aborting',
      intId,
    );
    useChatStore.setState({
      interruptedMessageId: null,
      error: i18n.t('chat.noContentContinue'),
    });
    return;
  }
  useChatStore.setState({
    continuingId: intId,
    skipThinking: false,
    pendingVersions: null,
    pendingThinkingVersions: null,
  });
  // 续写使用对话中选中的模型（与 submitRequirement 同一解析路径），
  // 后端按该模型解析 key/base_url，避免落到 config 默认模型。
  let model: string | undefined;
  try {
    const keys = await listKeys();
    const activeKeys = keys.filter((k) => k.is_active);
    const persistedModel = localStorage.getItem('ragbase-selected-model');
    model = resolveKey(activeKeys, persistedModel ?? undefined).model;
  } catch {
    // Key vault unavailable — backend falls back to the default model
  }
  const prevRunId = s.currentRunId;
  if (prevRunId) disconnectRun(prevRunId);
  useChatStore.setState({ status: 'loading', error: null, result: null });
  try {
    // 原问题 = 被中断消息的前一条用户消息（prefix/partial 机制需要它做无缝续写）。
    const prevUser = [...s.messages]
      .slice(0, idx)
      .reverse()
      .find((m) => m.role === 'user');
    const resp = await resumeRun(
      continuation,
      s.currentSessionId || undefined,
      interruptedMsg.thinking,
      model,
      prevUser?.content,
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
    useChatStore.setState({
      status: 'error',
      error: errMsg,
      continuingId: null,
    });
  }
}
