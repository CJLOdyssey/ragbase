import { memo, useCallback } from 'react';
import { Bot, PanelLeft, Sparkles } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { Conversation } from '../../types/AgentStudio';
import ConversationsList from './sidebar/ConversationsList';
import UserMenu from './sidebar/UserMenu';

interface AgentStudioSidebarProps {
  conversations: Conversation[];
  activeConvId: string | null;
  selectedAgentId: string | null;
  isUserMenuOpen: boolean;
  setIsUserMenuOpen: (open: boolean) => void;
  setIsSettingsOpen: (open: boolean) => void;
  setIsApiOpen: (open: boolean) => void;
  setSelectedAgentId: (id: string | null) => void;
  setActiveConvId: (id: string | null) => void;
  setInputValue: (value: string) => void;
  onDeleteConversation: (convId: string) => void;
  onNewChat: () => void;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  onOpenWorkstation: () => void;
}

const AgentStudioSidebar = memo(function AgentStudioSidebar({
  conversations,
  activeConvId,
  selectedAgentId,
  isUserMenuOpen,
  setIsUserMenuOpen,
  setIsSettingsOpen,
  setIsApiOpen,
  setSelectedAgentId,
  setActiveConvId,
  setInputValue,
  onDeleteConversation,
  onNewChat,
  isSidebarOpen,
  onToggleSidebar,
  onOpenWorkstation,
}: AgentStudioSidebarProps) {
  const { t } = useTranslation();

  const handleConvSelect = useCallback(
    (conv: Conversation) => {
      setSelectedAgentId(null);
      setActiveConvId(conv.id);
      setInputValue(conv.title);
    },
    [setSelectedAgentId, setActiveConvId, setInputValue],
  );

  const handleConvDelete = useCallback(
    (convId: string) => {
      onDeleteConversation(convId);
    },
    [onDeleteConversation],
  );

  return (
    <aside
      className={`flex flex-col h-full bg-[var(--color-surface-sidebar)] border-r border-r-[var(--color-border-subtle)] shrink-0 overflow-hidden transition-[width,min-width,opacity,border-width] duration-200 ease-in-out ${isSidebarOpen ? 'w-[var(--da-sidebar-width)] min-w-[var(--da-sidebar-width)] opacity-100' : 'w-0 min-w-0 opacity-0 pointer-events-none border-r-0'}`}
    >
      {/* Header: logo + toggle */}
      <div className="flex items-center justify-between gap-3 px-4 py-3 shrink-0 mb-6">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-[var(--color-accent)]/10 flex items-center justify-center text-[var(--color-accent)] shrink-0">
            <Bot size={22} />
          </div>
          <span className="font-semibold text-lg text-[var(--color-text-primary)] tracking-[-0.02em] truncate">
            AgentStudio
          </span>
        </div>
        <button
          className="flex items-center justify-center w-9 h-9 bg-transparent border-none rounded-lg text-[var(--color-text-muted)] cursor-pointer transition-[color,background] duration-150 hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)] shrink-0"
          onClick={onToggleSidebar}
          aria-label="Collapse sidebar"
        >
          <PanelLeft size={20} />
        </button>
      </div>

      {/* New Chat - primary action */}
      <div className="px-4 shrink-0">
        <button
          className="w-full flex items-center justify-center gap-2 h-10 px-4 bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-full text-sm font-medium text-[var(--color-text-primary)] cursor-pointer hover:bg-[var(--color-surface-hover)] active:scale-[0.98] transition-[transform] duration-150"
          onClick={onNewChat}
        >
          <Sparkles size={16} className="text-[var(--color-text-muted)]" />
          <span>{t('sidebar.newChat')}</span>
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 pt-7 px-4 flex flex-col">
        <div className="flex flex-col min-h-0 flex-1">
          <div className="px-2 py-0.5 text-sm font-medium leading-[22px] text-[var(--color-text-tertiary)] shrink-0">
            {t('sidebar.recentConversations')}
          </div>
          <ConversationsList
            conversations={conversations}
            activeConvId={activeConvId}
            selectedAgentId={selectedAgentId}
            onSelect={handleConvSelect}
            onDelete={handleConvDelete}
            onRename={(_id) => {
              /* TODO */
            }}
            onPin={(_id) => {
              /* TODO */
            }}
          />
        </div>
      </div>

      {/* User menu - bottom pinned */}
      <UserMenu
        isUserMenuOpen={isUserMenuOpen}
        setIsUserMenuOpen={setIsUserMenuOpen}
        setIsSettingsOpen={setIsSettingsOpen}
        setIsApiOpen={setIsApiOpen}
        onOpenWorkstation={onOpenWorkstation}
      />
    </aside>
  );
});

export default AgentStudioSidebar;
