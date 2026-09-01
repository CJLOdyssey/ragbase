import { RefObject, useCallback } from 'react';
import { Virtuoso, VirtuosoHandle } from 'react-virtuoso';
import type { Message } from '../../types/studio';
import {
  continueGeneration,
  editAndRegenerate,
  regenerateMessage,
} from '../../stores/chatActions';
import { useChatStore } from '../../stores/chatStore';
import { useMessageFeedback } from '../../hooks/useMessageFeedback';
import BrowserFrame from './BrowserFrame';
import TeamMessage from './TeamMessage';

interface Props {
  hasMessages: boolean;
  displayMessages: Message[];
  messagesEndRef: RefObject<HTMLDivElement>;
  onSwitchBranch: (runId: string) => void;
  virtuosoRef?: RefObject<VirtuosoHandle>;
}

export default function MessagesPanel({
  hasMessages,
  displayMessages,
  messagesEndRef,
  onSwitchBranch,
  virtuosoRef,
}: Props) {
  const interruptedMessageId = useChatStore((s) => s.interruptedMessageId);
  const continuingId = useChatStore((s) => s.continuingId);
  // 反馈提交（store 更新 + 后端请求 + 提示）收敛到 hook，组件不直接发请求。
  const handleThumbsFeedback = useMessageFeedback();
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

  if (hasMessages) {
    return (
        <div
          className="max-w-[min(900px,100vw)] mx-auto w-full flex flex-col px-4 py-5 pb-8 md:px-6 md:py-6 md:pb-12"
          aria-live="polite"
        >
        <Virtuoso
          ref={virtuosoRef}
          style={{ flex: 1 }}
          totalCount={displayMessages.length + 2} // +2 for BrowserFrame and scroll anchor
          itemContent={(index) => {
            // Last item: BrowserFrame + scroll anchor
            if (index >= displayMessages.length) {
              return (
                <>
                  <BrowserFrame />
                  <div ref={messagesEndRef} />
                </>
              );
            }
            const msg = displayMessages[index];
            return (
              <div className="mb-4 md:mb-6">
                <TeamMessage
                  msg={msg}
                  onEditMessage={handleEditMessage}
                  onRegenerate={handleRegenerate}
                  showContinue={msg.id === interruptedMessageId}
                  onContinue={continueGeneration}
                  onSwitchUserVersion={handleSwitchUserVersion}
                  onSwitchAnswer={handleSwitchAnswerVersion}
                  isContinuing={msg.id === continuingId}
                  onThumbsFeedback={handleThumbsFeedback}
                />
              </div>
            );
          }}
        />
      </div>
    );
  }

  return null;
}
