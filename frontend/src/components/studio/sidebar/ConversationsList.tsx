import { memo, useEffect, useMemo, useRef, useState } from 'react';
import type { Agent, Conversation } from '../../../types/AgentStudio';
import {
  Cpu,
  MessageSquare,
  MoreVertical,
  Pencil,
  Pin,
  Trash2,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Virtuoso } from 'react-virtuoso';

interface ConversationsListProps {
  conversations: Conversation[];
  activeConvId: string | null;
  selectedAgentId: string | null;
  agents?: Agent[];
  onSelect: (conv: Conversation) => void;
  onDelete: (convId: string) => void;
  onRename?: (convId: string) => void;
  onPin?: (convId: string) => void;
}

// Fallback: if the prop is empty but localStorage has conversations (e.g.
// when React state propagation fails through memo boundaries), read directly.
function readLocalConversations(): Conversation[] | null {
  try {
    const saved = localStorage.getItem('agentstudio-conversations');
    if (!saved) return null;
    const parsed = JSON.parse(saved) as Conversation[];
    return parsed.length > 0 ? parsed : null;
  } catch {
    return null;
  }
}

const ConversationsList = memo(function ConversationsList({
  conversations: conversationsProp,
  activeConvId,
  selectedAgentId,
  agents = [],
  onSelect,
  onDelete,
  onRename,
  onPin,
}: ConversationsListProps) {
  const { t, i18n } = useTranslation();
  const [openMenuConvId, setOpenMenuConvId] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on outside click
  useEffect(() => {
    if (!openMenuConvId) return;
    const h = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpenMenuConvId(null);
      }
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [openMenuConvId]);

  // Fallback: if the prop is empty but localStorage has conversations (e.g.
  // when React state propagation fails through memo boundaries), read directly.
  const [localFallback, setLocalFallback] = useState<Conversation[] | null>(
    null,
  );
  useEffect(() => {
    if (conversationsProp.length === 0) {
      setLocalFallback(readLocalConversations());
    } else {
      setLocalFallback(null);
    }
  }, [conversationsProp]);
  const conversations = localFallback ?? conversationsProp;

  const groupedConversations = useMemo(() => {
    const groups = {
      today: [] as Conversation[],
      yesterday: [] as Conversation[],
      threeDays: [] as Conversation[],
      sevenDays: [] as Conversation[],
      month: [] as Conversation[],
      older: [] as Conversation[],
    };

    const now = new Date();
    const todayStart = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate(),
    ).getTime();
    const oneDay = 24 * 60 * 60 * 1000;

    conversations.forEach((conv) => {
      const convDate = new Date(conv.updatedAt);
      const convStart = new Date(
        convDate.getFullYear(),
        convDate.getMonth(),
        convDate.getDate(),
      ).getTime();
      const diffDays = Math.floor((todayStart - convStart) / oneDay);

      if (diffDays <= 0) {
        groups.today.push(conv);
      } else if (diffDays === 1) {
        groups.yesterday.push(conv);
      } else if (diffDays <= 3) {
        groups.threeDays.push(conv);
      } else if (diffDays <= 7) {
        groups.sevenDays.push(conv);
      } else if (diffDays <= 30) {
        groups.month.push(conv);
      } else {
        groups.older.push(conv);
      }
    });

    return groups;
  }, [conversations]);

  const agentMap = useMemo(() => {
    const map = new Map<string, Agent>();
    agents.forEach((a) => map.set(a.id, a));
    return map;
  }, [agents]);

  const nonEmptyGroups = useMemo(() => {
    return [
      { label: t('sidebar.today'), items: groupedConversations.today },
      { label: t('sidebar.yesterday'), items: groupedConversations.yesterday },
      { label: t('sidebar.threeDays'), items: groupedConversations.threeDays },
      { label: t('sidebar.sevenDays'), items: groupedConversations.sevenDays },
      { label: t('sidebar.month'), items: groupedConversations.month },
      { label: t('sidebar.older'), items: groupedConversations.older },
    ].filter((g) => g.items.length > 0);
  }, [groupedConversations, t]);

  if (nonEmptyGroups.length === 0) return null;

  const flatItems = nonEmptyGroups.flatMap((g) => [
    { type: 'group' as const, label: g.label },
    ...g.items.map((conv) => ({ type: 'item' as const, conv })),
  ]);

  const renderConversationItem = (conv: Conversation) => {
    const agent = conv.agentId ? agentMap.get(conv.agentId) : undefined;
    const AgentIcon = agent?.icon;
    const isActive = activeConvId === conv.id && !selectedAgentId;
    return (
      <div
        key={conv.id}
        className={`group flex items-center py-2 pl-2 pr-1 rounded-md cursor-pointer transition-colors duration-150 gap-1 hover:bg-[var(--color-surface-hover)] ${isActive ? 'bg-[var(--color-accent)]/8' : ''}`}
        onClick={() => onSelect(conv)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onSelect(conv);
          }
        }}
        tabIndex={0}
        role="button"
        aria-selected={isActive}
      >
        <div className="flex-1 min-w-0">
          <div className="text-base text-[var(--color-text-primary)] leading-[1.3] overflow-hidden text-ellipsis whitespace-nowrap flex items-center gap-1.5">
            {conv.kind === 'agent' ? (
              <span
                className="shrink-0 flex items-center"
                style={{ color: agent?.color || 'var(--color-accent)' }}
              >
                {agent && AgentIcon ? (
                  <AgentIcon size={14} />
                ) : (
                  <Cpu size={14} />
                )}
              </span>
            ) : (
              <span
                className="shrink-0 flex items-center"
                style={{ color: 'var(--color-text-tertiary)' }}
              >
                <MessageSquare size={14} />
              </span>
            )}
            {Array.from(conv.title).length > 28
              ? Array.from(conv.title).slice(0, 28).join('') + '...'
              : conv.title}
          </div>
          <div className="text-sm text-[var(--color-text-tertiary)] mt-1 flex items-center gap-1">
            {agent && (
              <span className="text-[var(--color-text-secondary)] font-medium">
                {agent.name}
              </span>
            )}
            {conv.messages.filter((m) => m.role === 'agent').length > 0
              ? t('sidebar.replied')
              : t('sidebar.pendingReply')}
            {' · '}
            {new Date(conv.updatedAt).toLocaleDateString(
              i18n.language === 'en-US' ? 'en-US' : 'zh-CN',
              { month: 'short', day: 'numeric' },
            )}
          </div>
        </div>
        <div className="relative shrink-0">
          <button
            className="bg-transparent border-none p-1 rounded cursor-pointer text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] flex items-center justify-center w-[24px] h-[24px] shrink-0 opacity-0 group-hover:opacity-70 hover:opacity-100 transition-all duration-150"
            onClick={(e) => {
              e.stopPropagation();
              setOpenMenuConvId(openMenuConvId === conv.id ? null : conv.id);
            }}
            aria-label="更多"
          >
            <MoreVertical size={15} />
          </button>
          {openMenuConvId === conv.id && (
            <div
              ref={menuRef}
              className="absolute right-0 top-full mt-1 min-w-[120px] bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-lg shadow-[0_4px_16px_rgba(0,0,0,0.18)] z-[var(--z-dropdown)] flex flex-col p-1 origin-top-right animate-[popoverScaleIn_0.12s_cubic-bezier(0.16,1,0.3,1)]"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                className="flex items-center gap-2 w-full px-3 py-1.5 text-sm text-[var(--color-text-primary)] bg-transparent border-none rounded-md cursor-pointer transition-colors duration-100 text-left hover:bg-[var(--color-surface-hover)]"
                onClick={() => {
                  setOpenMenuConvId(null);
                  onRename?.(conv.id);
                }}
              >
                <Pencil size={13} />
                重命名
              </button>
              <button
                className="flex items-center gap-2 w-full px-3 py-1.5 text-sm text-[var(--color-text-primary)] bg-transparent border-none rounded-md cursor-pointer transition-colors duration-100 text-left hover:bg-[var(--color-surface-hover)]"
                onClick={() => {
                  setOpenMenuConvId(null);
                  onPin?.(conv.id);
                }}
              >
                <Pin size={13} />
                顶置
              </button>
              <div className="h-px bg-[var(--color-border-subtle)] mx-2 my-1" />
              <button
                className="flex items-center gap-2 w-full px-3 py-1.5 text-sm text-[var(--color-danger)] bg-transparent border-none rounded-md cursor-pointer transition-colors duration-100 text-left hover:bg-[var(--color-danger)]/10"
                onClick={() => {
                  setOpenMenuConvId(null);
                  onDelete(conv.id);
                }}
              >
                <Trash2 size={13} />
                删除
              </button>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col gap-2 mb-1 min-h-0 flex-1">
      <Virtuoso
        style={{ height: '100%' }}
        data={flatItems}
        itemContent={(_index: number, item: (typeof flatItems)[number]) =>
          item.type === 'group' ? (
            <div className="text-sm font-medium text-[var(--color-text-tertiary)] tracking-[0.03em] py-2 px-3">
              {item.label}
            </div>
          ) : (
            renderConversationItem(item.conv)
          )
        }
      />
    </div>
  );
});

export default ConversationsList;
