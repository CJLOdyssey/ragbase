import { memo, useCallback, useMemo, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import {
  Bot,
  ChevronDown,
  ChevronRight,
  Clock,
  Database,
  FileText,
  LayoutGrid,
  LineChart,
  PanelLeft,
  Sparkles,
  Users,
  type LucideIcon,
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
  /** 移动端：侧边栏渲染为覆盖式抽屉（fixed + 遮罩），关闭按钮点击后收起 */
  isMobile: boolean;
  onCloseSidebar: () => void;
  activeView: ManageView;
  onNavigate: (view: ManageView) => void;
}

const NAV_BTN =
  'w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] transition-colors duration-150 cursor-pointer border-none bg-transparent text-left';

const NAV_BTN_ACTIVE =
  'bg-[var(--color-surface-hover)] text-[var(--color-text-primary)]';

interface NavGroup {
  labelKey: string;
  items: Array<{ view: ManageView; icon: LucideIcon; labelKey: string }>;
  adminOnly?: boolean;
}

const NAV_GROUPS: NavGroup[] = [
  {
    labelKey: 'sidebar.group.resources',
    items: [
      { view: 'prompts', icon: FileText, labelKey: 'sidebar.nav.prompts' },
      { view: 'assets', icon: LayoutGrid, labelKey: 'sidebar.nav.assets' },
    ],
  },
  {
    labelKey: 'sidebar.group.knowledge',
    items: [
      {
        view: 'knowledge-bases',
        icon: Database,
        labelKey: 'sidebar.nav.knowledgeBases',
      },
    ],
  },
  {
    labelKey: 'sidebar.group.analytics',
    items: [
      {
        view: 'monitoring',
        icon: LineChart,
        labelKey: 'sidebar.nav.qualityReport',
      },
      {
        view: 'retrieval-logs',
        icon: Clock,
        labelKey: 'sidebar.nav.retrievalLogs',
      },
    ],
  },
  {
    labelKey: 'sidebar.group.admin',
    items: [
      {
        view: 'admin-users',
        icon: Users,
        labelKey: 'sidebar.nav.userManagement',
      },
    ],
    adminOnly: true,
  },
];

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
  isMobile,
  onCloseSidebar,
  activeView,
  onNavigate,
}: RagBaseSidebarProps) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [memorySessionId, setMemorySessionId] = useState<string | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(
    new Set(),
  );

  const isAdmin = useMemo(() => {
    return user?.roles?.includes('admin') ?? false;
  }, [user]);

  const visibleGroups = useMemo(() => {
    return NAV_GROUPS.filter((group) => !group.adminOnly || isAdmin);
  }, [isAdmin]);

  const toggleGroup = useCallback((labelKey: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(labelKey)) {
        next.delete(labelKey);
      } else {
        next.add(labelKey);
      }
      return next;
    });
  }, []);

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
    <>
      {/* 移动端覆盖遮罩：抽屉打开时拦截点击关闭 */}
      {isMobile && isSidebarOpen && (
        <div
          data-testid="sidebar-overlay"
          className="fixed inset-0 z-40 bg-[var(--color-overlay)] md:hidden"
          aria-hidden="true"
          onClick={onCloseSidebar}
        />
      )}
      <aside
        className={`flex flex-col h-full bg-[var(--color-surface-sidebar)] border-r border-r-[var(--color-border-subtle)] shrink-0 overflow-hidden transition-[width,min-width,opacity,border-width,transform] duration-200 ease-in-out ${
          isMobile
            ? `fixed inset-y-0 left-0 z-50 w-[var(--da-sidebar-width)] max-w-[85vw] ${
                isSidebarOpen
                  ? 'translate-x-0 shadow-2xl'
                  : '-translate-x-full pointer-events-none border-r-0'
              } md:translate-x-0 md:pointer-events-auto`
            : `relative ${isSidebarOpen
                ? 'w-[var(--da-sidebar-width)] min-w-[var(--da-sidebar-width)] opacity-100'
                : 'w-0 min-w-0 opacity-0 pointer-events-none border-r-0'}`
        }`}
      >
        {/* Header: logo + toggle */}
        <div className="flex items-center justify-between gap-3 px-4 py-3 shrink-0 mb-4">
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
            onClick={isMobile ? onCloseSidebar : onToggleSidebar}
            aria-label={
              isMobile ? 'Close sidebar' : 'Collapse sidebar'
            }
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

      {/* Grouped navigation */}
      <nav className="px-4 shrink-0 mt-4 flex flex-col gap-3">
        {visibleGroups.map((group) => {
          const isCollapsed = collapsedGroups.has(group.labelKey);
          return (
            <div key={group.labelKey} className="flex flex-col gap-0.5">
              <button
                onClick={() => toggleGroup(group.labelKey)}
                className="flex items-center justify-between w-full px-3 py-1 text-sm font-medium text-[var(--color-text-tertiary)] bg-transparent border-none cursor-pointer hover:text-[var(--color-text-secondary)] transition-colors"
              >
                <span>{t(group.labelKey)}</span>
                {isCollapsed ? (
                  <ChevronRight size={14} />
                ) : (
                  <ChevronDown size={14} />
                )}
              </button>
              {!isCollapsed &&
                group.items.map(({ view, icon: Icon, labelKey }) => (
                  <button
                    key={view}
                    onClick={() => onNavigate(view)}
                    className={`${NAV_BTN} ${activeView === view ? NAV_BTN_ACTIVE : ''}`}
                  >
                    <Icon size={16} className="shrink-0" />
                    <span>{t(labelKey)}</span>
                  </button>
                ))}
            </div>
          );
        })}
      </nav>

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
    </>
  );
});

export default RagBaseSidebar;
