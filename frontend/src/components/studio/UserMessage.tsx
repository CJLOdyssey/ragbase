import { useState } from 'react';
import type * as React from 'react';
import { ChevronRight, GitBranch, Pencil } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { Message } from '../../types/studio';
import { switchBranch } from '../../stores/chatActions';
import { useChatStore } from '../../stores/chatStore';
import { CopyBtn } from './messages';
import { sanitizeHtml } from '../../utils/sanitize';

interface Props {
  msg: Message;
  onEditMessage?: (msgId: string, newContent: string) => void;
  onSwitchUserVersion?: (msgId: string, direction: 'prev' | 'next') => void;
}

export default function UserMessage({
  msg,
  onEditMessage,
  onSwitchUserVersion,
}: Props) {
  const { t, i18n } = useTranslation();
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState('');
  const [isBranchOpen, setIsBranchOpen] = useState(false);

  const allRuns = useChatStore((s) => s.allRuns);
  const activeRunId = useChatStore((s) => s.activeRunId);

  const userVersions = msg.userVersions || [msg.content];
  const currentUserVersion = msg.currentUserVersion ?? 0;
  // 分支点：当前 run 的子节点 > 1（续聊 + 编辑分支并存）
  const currentRunId = msg.runId ?? activeRunId ?? '';
  const children = Object.values(allRuns).filter(
    (r) => r.parent_run_id === currentRunId && r.id !== currentRunId,
  );
  const hasBranches = children.length > 1;
  const time = msg.timestamp
    ? new Date(msg.timestamp).toLocaleTimeString(
        i18n.language === 'en-US' ? 'en-US' : 'zh-CN',
        {
          hour: '2-digit',
          minute: '2-digit',
        },
      )
    : '';

  const startEditing = () => {
    setEditText(msg.content);
    setIsEditing(true);
  };

  const cancelEdit = () => {
    setIsEditing(false);
    setEditText('');
  };

  const saveEdit = () => {
    if (editText.trim() && onEditMessage) {
      onEditMessage(msg.id, editText.trim());
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      saveEdit();
    }
    if (e.key === 'Escape') {
      cancelEdit();
    }
  };

  if (isEditing) {
    return (
      <div className="flex justify-end w-full">
        <div className="flex items-center gap-2 w-full px-4 py-3 border border-[var(--color-border)] rounded-xl bg-[var(--color-surface-raised)]">
          <textarea
            className="flex-1 border-none bg-transparent text-[var(--color-text-primary)] text-base font-[inherit] leading-[1.5] resize-none outline-none min-h-6 max-h-[120px] placeholder:text-[var(--color-text-muted)]"
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            onKeyDown={handleKeyDown}
            autoFocus
            rows={1}
          />
          <div className="flex gap-2 flex-shrink-0">
            <button
              className="px-4 py-1.5 border border-[var(--color-border)] rounded-lg bg-transparent text-[var(--color-text-secondary)] text-sm cursor-pointer transition-colors duration-150 hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]"
              onClick={cancelEdit}
            >
              {t('common.cancel')}
            </button>
            <button
              className="px-4 py-1.5 border border-[var(--color-border)] rounded-lg bg-transparent text-[var(--color-text-secondary)] text-sm cursor-pointer transition-colors duration-150 hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)] disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={saveEdit}
            >
              {t('common.send')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 flex-row-reverse">
      <div className="flex flex-col gap-1 items-end max-w-[80%]">
        <div className="flex flex-col items-end w-fit max-w-full">
          <div className="px-4 py-3 rounded-[12px_12px_4px_12px] bg-[var(--color-surface-raised)] text-[var(--color-text-primary)]">
            {sanitizeHtml(msg.content)}
          </div>
          <div className="flex items-center gap-2 mt-1 w-full justify-end">
            <CopyBtn text={msg.content} label={t('teamMessage.copy')} />
            <button
              className="px-1.5 py-1 bg-transparent border-none rounded text-[var(--color-text-muted)] cursor-pointer flex items-center transition-colors duration-150 hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]"
              onClick={startEditing}
              title={t('teamMessage.edit')}
              aria-label={t('teamMessage.edit')}
            >
              <Pencil size={12} />
            </button>
            {userVersions.length > 1 && (
              <div className="flex items-center gap-0.5">
                <button
                  className="flex items-center justify-center w-6 h-6 bg-transparent border border-[var(--color-border)] rounded text-[var(--color-text-muted)] cursor-pointer transition-colors duration-150 p-0 hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-strong)] disabled:opacity-35 disabled:cursor-not-allowed"
                  onClick={() => onSwitchUserVersion?.(msg.id, 'prev')}
                  disabled={currentUserVersion === 0}
                  aria-label="Previous user version"
                >
                  <ChevronRight size={12} className="rotate-180" />
                </button>
                <span className="text-xs text-[var(--color-text-muted)] min-w-7 text-center select-none">
                  {currentUserVersion + 1}/{userVersions.length}
                </span>
                <button
                  className="flex items-center justify-center w-6 h-6 bg-transparent border border-[var(--color-border)] rounded text-[var(--color-text-muted)] cursor-pointer transition-colors duration-150 p-0 hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-strong)] disabled:opacity-35 disabled:cursor-not-allowed"
                  onClick={() => onSwitchUserVersion?.(msg.id, 'next')}
                  disabled={currentUserVersion === userVersions.length - 1}
                  aria-label="Next user version"
                >
                  <ChevronRight size={12} />
                </button>
              </div>
            )}
            {hasBranches && (
              <div className="relative">
                <button
                  className="flex items-center justify-center w-6 h-6 bg-transparent border border-[var(--color-border)] rounded text-[var(--color-text-muted)] cursor-pointer transition-colors duration-150 p-0 hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-strong)]"
                  onClick={() => setIsBranchOpen(!isBranchOpen)}
                  aria-label="Switch branch"
                  title={t('teamMessage.switchBranch') || '切换分支'}
                >
                  <GitBranch size={12} />
                </button>
                {isBranchOpen && (
                  <div className="absolute right-0 top-7 z-20 min-w-[220px] max-w-[320px] bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-lg shadow-lg p-1">
                    {children.map((child) => {
                      const isActive = child.id === activeRunId;
                      return (
                        <button
                          key={child.id}
                          className={`flex items-center gap-2 w-full px-2 py-1.5 border-none rounded-md bg-transparent text-left text-xs cursor-pointer transition-colors duration-150 hover:bg-[var(--color-surface-hover)] ${isActive ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-secondary)]'}`}
                          onClick={() => {
                            switchBranch(child.id);
                            setIsBranchOpen(false);
                          }}
                        >
                          <GitBranch size={10} className="flex-shrink-0" />
                          <span className="overflow-hidden text-ellipsis whitespace-nowrap">
                            {child.requirement || '(未命名分支)'}
                          </span>
                          {isActive && (
                            <span className="ml-auto text-[var(--color-accent)]">
                              ●
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
            {time && (
              <span className="block text-xs text-[var(--color-text-muted)] mt-1 ml-0">
                {time}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
