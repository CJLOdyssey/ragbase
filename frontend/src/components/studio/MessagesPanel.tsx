import { RefObject, useCallback } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import type { ChatMessage } from '../../types';
import type { Agent, Message } from '../../types/studio';
import {
  continueGeneration,
  editAndRegenerate,
  regenerateMessage,
} from '../../stores/chatActions';
import { useChatStore } from '../../stores/chatStore';
import BrowserFrame from './BrowserFrame';
import TeamMessage from './TeamMessage';

// 模型消息答案切换：同一用户问题的不同回答（重新生成链），纯本地联动。
// 只更新模型消息 content/thinking/currentUserVersion，不动用户消息与分支。
function applyLocalAnswerSwitch(
  prev: ChatMessage[],
  msgId: string,
  runIds: string[],
  nv: number,
  runTurns: Record<string, { content: string; thinking: string }>,
): ChatMessage[] {
  const runId = runIds[nv];
  const turn = runTurns[runId];
  if (!turn) return prev;
  return prev.map((m) =>
    m.id === msgId
      ? {
          ...m,
          content: turn.content,
          thinking: turn.thinking,
          currentUserVersion: nv,
        }
      : m,
  );
}

interface Props {
  showAgentChat: boolean;
  hasMessages: boolean;
  allAgents: Agent[];
  displayMessages: Message[];
  messagesEndRef: RefObject<HTMLDivElement>;
  onSwitchBranch: (runId: string) => void;
}

export default function MessagesPanel({
  showAgentChat,
  hasMessages,
  allAgents,
  displayMessages,
  messagesEndRef,
  onSwitchBranch,
}: Props) {
  const reduce = useReducedMotion();
  const interruptedMessageId = useChatStore((s) => s.interruptedMessageId);
  const continuingId = useChatStore((s) => s.continuingId);
  const setThumbsFeedback = useChatStore((s) => s.setThumbsFeedback);
  const handleEditMessage = useCallback((msgId: string, newContent: string) => {
    // Edit → save content + regenerate the following answer (merged into its versions).
    void editAndRegenerate(msgId, newContent);
  }, []);

  const handleRegenerate = useCallback(
    (msgId: string) => {
      const idx = displayMessages.findIndex((m) => m.id === msgId);
      if (idx >= 0) {
        void regenerateMessage(idx);
      }
    },
    [displayMessages],
  );

  // 模型消息分页：同一用户问题的不同回答（重新生成链），纯本地切换，
  // 不联动用户消息、不切分支。
  const handleSwitchAnswerVersion = useCallback(
    (msgId: string, direction: 'prev' | 'next') => {
      const s = useChatStore.getState();
      const msg = s.messages.find((m) => m.id === msgId);
      if (!msg) return;
      const versions = msg.userVersions;
      const runIds = msg.versionRunIds;
      if (!versions || !runIds || versions.length < 2) return;
      const cur = msg.currentUserVersion ?? versions.length - 1;
      const nv =
        direction === 'prev'
          ? Math.max(0, cur - 1)
          : Math.min(versions.length - 1, cur + 1);
      if (nv === cur) return;
      useChatStore.setState((prev) => ({
        messages: applyLocalAnswerSwitch(
          prev.messages,
          msg.id,
          runIds,
          nv,
          s.runTurns,
        ),
      }));
    },
    [],
  );

  const handleSwitchUserVersion = useCallback(
    (msgId: string, direction: 'prev' | 'next') => {
      const s = useChatStore.getState();
      const userMsg = s.messages.find((m) => m.id === msgId);
      if (!userMsg) return;
      const versions = userMsg.userVersions;
      const versionRunIds = userMsg.versionRunIds;
      if (!versions || versions.length < 2) return;
      const cur = userMsg.currentUserVersion ?? versions.length - 1;
      const nv =
        direction === 'prev'
          ? Math.max(0, cur - 1)
          : Math.min(versions.length - 1, cur + 1);
      if (nv === cur) return;
      // 用户版本 = 分支语义：始终整分支切换（视图加载目标分支全部消息），
      // 不做本地联动 — 本地联动只用于模型消息分页（handleSwitchAnswerVersion）。
      const runId = versionRunIds?.[nv];
      if (!runId) return;
      void onSwitchBranch(runId);
    },
    [onSwitchBranch],
  );

  const handleThumbsFeedback = useCallback(
    (msgId: string, value: 'up' | 'down' | null) =>
      setThumbsFeedback(msgId, value),
    [setThumbsFeedback],
  );

  if (showAgentChat) {
    return (
      <div
        className="max-w-[min(900px,85vw)] mx-auto w-full flex flex-col gap-6 px-6 py-6 pb-12"
        aria-live="polite"
      >
        {displayMessages.map((msg) => (
          <motion.div
            key={msg.id}
            initial={reduce ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <TeamMessage
              msg={msg}
              allAgents={allAgents}
              onEditMessage={handleEditMessage}
              onRegenerate={handleRegenerate}
              showContinue={msg.id === interruptedMessageId}
              onContinue={continueGeneration}
              onSwitchUserVersion={(id, dir) => {
                const m = useChatStore
                  .getState()
                  .messages.find((x) => x.id === id);
                if (m?.role === 'user') {
                  handleSwitchUserVersion(id, dir);
                } else {
                  handleSwitchAnswerVersion(id, dir);
                }
              }}
              isContinuing={msg.id === continuingId}
              onThumbsFeedback={handleThumbsFeedback}
            />
          </motion.div>
        ))}
        <BrowserFrame />
        <div ref={messagesEndRef} />
      </div>
    );
  }

  if (hasMessages) {
    return (
      <div
        className="max-w-[min(900px,85vw)] mx-auto w-full flex flex-col gap-6 px-6 py-6 pb-12"
        aria-live="polite"
      >
        {displayMessages.map((msg) => (
          <motion.div
            key={msg.id}
            initial={reduce ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <TeamMessage
              msg={msg}
              allAgents={allAgents}
              onEditMessage={handleEditMessage}
              onRegenerate={handleRegenerate}
              showContinue={msg.id === interruptedMessageId}
              onContinue={continueGeneration}
              onSwitchUserVersion={(id, dir) => {
                const m = useChatStore
                  .getState()
                  .messages.find((x) => x.id === id);
                if (m?.role === 'user') {
                  handleSwitchUserVersion(id, dir);
                } else {
                  handleSwitchAnswerVersion(id, dir);
                }
              }}
              isContinuing={msg.id === continuingId}
              onThumbsFeedback={handleThumbsFeedback}
            />
          </motion.div>
        ))}
        <BrowserFrame />
        <div ref={messagesEndRef} />
      </div>
    );
  }

  return null;
}
