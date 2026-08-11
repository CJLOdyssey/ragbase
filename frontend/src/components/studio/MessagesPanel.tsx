import { RefObject, useCallback } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import type { Agent, Message } from '../../types/studio';
import {
  continueGeneration,
  editAndRegenerate,
  regenerateMessage,
} from '../../stores/chatActions';
import { useChatStore } from '../../stores/chatStore';
import BrowserFrame from './BrowserFrame';
import TeamMessage from './TeamMessage';

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

  // 模型消息分页：同一用户问题的不同回答（重新生成链）也是分支（与用户
  // 消息 1:N）。切换 = 分支切换（父链 + 子孙链整体加载）：目标分支后续
  // 若有追问轮次，视图随之切到该分支的后续内容。目标 runId 由 store 计算。
  const handleSwitchAnswerVersion = useCallback(
    (msgId: string, direction: 'prev' | 'next') => {
      const runId = useChatStore
        .getState()
        .resolveAnswerVersionTarget(msgId, direction);
      if (!runId) return;
      void onSwitchBranch(runId);
    },
    [onSwitchBranch],
  );

  const handleSwitchUserVersion = useCallback(
    (msgId: string, direction: 'prev' | 'next') => {
      const runId = useChatStore
        .getState()
        .resolveUserVersionTarget(msgId, direction);
      if (!runId) return;
      // 用户版本 = 分支语义：始终整分支切换（视图加载目标分支全部消息）。
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
        {displayMessages.length === 0 ? (
          <LoadingSkeleton />
        ) : (
          displayMessages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={
                reduce || msg.thinkingDone ? false : { opacity: 0, y: 12 }
              }
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
                onSwitchUserVersion={handleSwitchUserVersion}
                onSwitchAnswer={handleSwitchAnswerVersion}
                isContinuing={msg.id === continuingId}
                onThumbsFeedback={handleThumbsFeedback}
              />
            </motion.div>
          ))
        )}
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
        {displayMessages.length === 0 ? (
          <LoadingSkeleton />
        ) : (
          displayMessages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={
                reduce || msg.thinkingDone ? false : { opacity: 0, y: 12 }
              }
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
                onSwitchUserVersion={handleSwitchUserVersion}
                onSwitchAnswer={handleSwitchAnswerVersion}
                isContinuing={msg.id === continuingId}
                onThumbsFeedback={handleThumbsFeedback}
              />
            </motion.div>
          ))
        )}
        <BrowserFrame />
        <div ref={messagesEndRef} />
      </div>
    );
  }

  return null;
}

function LoadingSkeleton() {
  return (
    <div
      className="flex flex-1 flex-col items-center justify-center py-24 text-sm text-[var(--color-text-muted)]"
      aria-busy="true"
    >
      <div className="h-4 w-40 mb-3 rounded bg-[var(--color-surface-raised)] animate-pulse" />
      <div className="h-4 w-56 rounded bg-[var(--color-surface-raised)] animate-pulse" />
      <div className="mt-4 text-[var(--color-text-muted)]">正在加载对话…</div>
    </div>
  );
}
