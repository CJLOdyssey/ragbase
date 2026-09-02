import { RefObject, useCallback } from 'react';
import { Virtuoso, VirtuosoHandle } from 'react-virtuoso';
import type { Message } from '../../types/studio';
import {
  continueGeneration,
  editAndRegenerate,
  regenerateMessage,
} from '../../stores/chatActions';
import { useChatStore } from '../../stores/chatStore';
import BrowserFrame from './BrowserFrame';
import TeamMessage from './TeamMessage';
import { useMessageFeedback } from '../../hooks/useMessageFeedback';

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
  const handleThumbsFeedback = useMessageFeedback();
  const handleEditMessage = useCallback((msgId: string, newContent: string) => {
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
      void onSwitchBranch(runId);
    },
    [onSwitchBranch],
  );

  if (hasMessages) {
    return (
      <div className="flex flex-col flex-1 min-h-0" aria-live="polite">
        <Virtuoso
          ref={virtuosoRef}
          style={{ flex: 1 }}
          totalCount={displayMessages.length}
          computeItemKey={(index) => displayMessages[index].id}
          itemContent={(index) => {
            const msg = displayMessages[index];
            return (
              <div className="max-w-[min(900px,100vw)] mx-auto w-full mb-4 md:mb-6 px-4 py-2 md:px-6">
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
        <BrowserFrame />
        <div ref={messagesEndRef} />
      </div>
    );
  }

  return null;
}
