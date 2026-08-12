import { listKeys, resumeRun } from '../api/client';
import { connectRun, disconnectRun } from '../api/websocket';
import i18n from '../i18n';
import Logger from '../utils/logger';
import { resolveKey } from './chatActionsUtils';
import { useChatStore } from './chatStore';
import { createStreamHandler } from './chatStreaming';

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
