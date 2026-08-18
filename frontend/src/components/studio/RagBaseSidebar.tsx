import { memo, useCallback, useState } from 'react';
import {
  BarChart3,
  BookText,
  Bot,
  Database,
  FileSearch,
  FileText,
  PanelLeft,
  Sparkles,
  Users,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { Conversation } from '../../types/studio';
import MemoryPanel from './MemoryPanel';
import type { ManageView } from './RagBaseWorkstation';
import ConversationsList from './sidebar/ConversationsList';
import UserMenu from './sidebar/UserMenu';

interface RagBaseSidebarProps {
  conversations: Conversation[];
  activeConvId: string | null;
  isUserMenuOpen: boolean;
  setIsUserMenuOpen: (open: boolean) => void;
  setIsSettingsOpen: (open: boolean) => void;
  setIsApiOpen: (open: boolean) => void;
  setActiveConvId: (id: string | null) => void;
  setInputValue: (value: string) => void;
  onDeleteConversation: (convId: string) => void;
  onRenameConversation: (convId: string, title: string) => void;
  onPinConversation: (convId: string) => void;
  onNewChat: () => void;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  activeView: ManageView;
  onNavigate: (view: ManageView) => void;
}

const NAV_BTN_BASE =
  'flex-1 flex items-center justify-center gap-1.5 h-8 rounded-md text-xs font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] transition-colors duration-150 cursor-pointer border-none bg-transparent';

const RagBaseSidebar = memo(function RagBaseSidebar({
  conversations,
  activeConvId,
  isUserMenuOpen,
  setIsUserMenuOpen,
  setIsSettingsOpen,
  setIsApiOpen,
  setActiveConvId,
  setInputValue,
  onDeleteConversation,
  onRenameConversation,
  onPinConversation,
  onNewChat,
  isSidebarOpen,
  onToggleSidebar,
  activeView,
  onNavigate,
}: RagBaseSidebarProps) {
  const { t } = useTranslation();
  const [memorySessionId, setMemorySessionId] = useState<string | null>(null);

  const handleConvSelect = useCallback(
    (conv: Conversation) => {
      setActiveConvId(conv.id);
      setInputValue(conv.title);
    },
    [setActiveConvId, setInputValue],
  );

  const handleConvDelete = useCallback(
    (convId: string) => {
      onDeleteConversation(convId);
    },
    [onDeleteConversation],
  );

  return (
    <aside
      className={`relative flex flex-col h-full bg-[var(--color-surface-sidebar)] border-r border-r-[var(--color-border-subtle)] shrink-0 overflow-hidden transition-[width,min-width,opacity,border-width] duration-200 ease-in-out ${isSidebarOpen ? 'w-[var(--da-sidebar-width)] min-w-[var(--da-sidebar-width)] opacity-100' : 'w-0 min-w-0 opacity-0 pointer-events-none border-r-0'}`}
    >
      {/* Header: logo + toggle */}
      <div className="flex items-center justify-between gap-3 px-4 py-3 shrink-0 mb-6">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-[var(--color-accent)]/10 flex items-center justify-center text-[var(--color-accent)] shrink-0">
            <Bot size={22} />
          </div>
          <span className="font-semibold text-lg text-[var(--color-text-primary)] tracking-[-0.02em] truncate">
            RagBase
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

      {/* Navigation links */}
      <div className="px-4 shrink-0 flex flex-col gap-1.5 mt-2">
        <div className="flex gap-1.5">
          <button
            onClick={() => onNavigate('prompts')}
            className={`${NAV_BTN_BASE} ${activeView === 'prompts' ? 'bg-[var(--color-surface-hover)] text-[var(--color-text-primary)]' : ''}`}
          >
            <BookText size={14} />
            <span>{t('prompts.title')}</span>
          </button>
          <button
            onClick={() => onNavigate('assets')}
            className={`${NAV_BTN_BASE} ${activeView === 'assets' ? 'bg-[var(--color-surface-hover)] text-[var(--color-text-primary)]' : ''}`}
          >
            <FileText size={14} />
            <span>{t('assets.title')}</span>
          </button>
          <button
            onClick={() => onNavigate('monitoring')}
            className={`${NAV_BTN_BASE} ${activeView === 'monitoring' ? 'bg-[var(--color-surface-hover)] text-[var(--color-text-primary)]' : ''}`}
          >
            <BarChart3 size={14} />
            <span>{t('monitoring.title')}</span>
          </button>
        </div>
        <div className="flex gap-1.5">
          <button
            onClick={() => onNavigate('retrieval-logs')}
            className={`${NAV_BTN_BASE} ${activeView === 'retrieval-logs' ? 'bg-[var(--color-surface-hover)] text-[var(--color-text-primary)]' : ''}`}
          >
            <FileSearch size={14} />
            <span>{t('retrievalLogs.navTitle')}</span>
          </button>
          <button
            onClick={() => onNavigate('knowledge-bases')}
            className={`${NAV_BTN_BASE} ${activeView === 'knowledge-bases' ? 'bg-[var(--color-surface-hover)] text-[var(--color-text-primary)]' : ''}`}
          >
            <Database size={14} />
            <span>{t('kb.navTitle')}</span>
          </button>
          <button
            onClick={() => onNavigate('admin-users')}
            className={`${NAV_BTN_BASE} ${activeView === 'admin-users' ? 'bg-[var(--color-surface-hover)] text-[var(--color-text-primary)]' : ''}`}
          >
            <Users size={14} />
            <span>{t('admin.navTitle')}</span>
          </button>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 pt-7 px-4 flex flex-col">
        <div className="flex flex-col min-h-0 flex-1 -mr-4">
          <div className="px-2 py-0.5 text-sm font-medium leading-[22px] text-[var(--color-text-tertiary)] shrink-0">
            {t('sidebar.recentConversations')}
          </div>
          <ConversationsList
            conversations={conversations}
            activeConvId={activeConvId}
            onSelect={handleConvSelect}
            onDelete={handleConvDelete}
            onRename={onRenameConversation}
            onPin={onPinConversation}
            onMemories={setMemorySessionId}
          />
        </div>
      </div>

      {/* Memory panel overlay */}
      {memorySessionId && (
        <div className="absolute inset-0 z-10 bg-[var(--color-surface-sidebar)] flex flex-col">
          <MemoryPanel
            sessionId={memorySessionId}
            onClose={() => setMemorySessionId(null)}
          />
        </div>
      )}

      {/* User menu - bottom pinned */}
      <UserMenu
        isUserMenuOpen={isUserMenuOpen}
        setIsUserMenuOpen={setIsUserMenuOpen}
        setIsSettingsOpen={setIsSettingsOpen}
        setIsApiOpen={setIsApiOpen}
      />
    </aside>
  );
});

export default RagBaseSidebar;
