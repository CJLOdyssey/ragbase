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
}

export default function MessagesPanel({
  showAgentChat,
  hasMessages,
  allAgents,
  displayMessages,
  messagesEndRef,
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

  const handleSwitchUserVersion = useCallback(
    (msgId: string, direction: 'prev' | 'next') => {
      const s = useChatStore.getState();
      const userMsg = s.messages.find((m) => m.id === msgId);
      const versions = userMsg?.userVersions;
      if (!versions || versions.length < 2) return;
      const cur = userMsg?.currentUserVersion ?? versions.length - 1;
      const nv =
        direction === 'prev'
          ? Math.max(0, cur - 1)
          : Math.min(versions.length - 1, cur + 1);
      if (nv === cur) return;
      // 分支语义：切版本 = 切分支，视图只保留本 turn（该 user 消息 + 其回答），
      // 分支点之后的轮次截断隐藏（DB 留存）。
      useChatStore.setState((prev) => {
        const uIdx = prev.messages.findIndex((m) => m.id === msgId);
        const aIdx = prev.messages.findIndex(
          (m, i) => i > uIdx && m.role !== 'user',
        );
        const end = aIdx >= 0 ? aIdx + 1 : prev.messages.length;
        return {
          messages: prev.messages.slice(0, end).map((m) =>
            m.id === msgId
              ? { ...m, content: versions[nv], currentUserVersion: nv }
              : m,
          ),
        };
      });
    },
    [],
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
              onSwitchUserVersion={handleSwitchUserVersion}
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
              onSwitchUserVersion={handleSwitchUserVersion}
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
