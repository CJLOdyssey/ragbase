import { lazy, Suspense, useCallback, useMemo, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { type VirtuosoHandle } from 'react-virtuoso';
import { useIsMobile } from '../../hooks/useMediaQuery';
import InputToolbar, { type InputToolbarHandle } from '../input/InputToolbar';
import HomeScreen from './HomeScreen';
import MessagesPanel from './MessagesPanel';
import Modals from './Modals';
import RagBaseSidebar from './RagBaseSidebar';
import WorkstationHeader from './WorkstationHeader';
import { useAutoScroll } from './useAutoScroll';
import { useDragAndDrop } from './useDragAndDrop';
import { useHomeState } from './useHomeState';
import { pathToView, viewToPath } from './viewRoutes';

const PromptLibraryPage = lazy(() => import('../prompts/PromptLibraryPage'));
const AssetsPage = lazy(() => import('../assets/AssetsPage'));
const QualityMonitor = lazy(() => import('../monitoring/QualityMonitor'));
const RetrievalLogPage = lazy(() => import('../retrieval-logs/RetrievalLogPage'));
const AdminUsersPage = lazy(() => import('../admin/AdminUsersPage'));
const KnowledgeBasePage = lazy(() => import('../knowledge-base/KnowledgeBasePage'));

export type ManageView =
  | 'chat'
  | 'prompts'
  | 'assets'
  | 'monitoring'
  | 'retrieval-logs'
  | 'admin-users'
  | 'knowledge-bases';

export default function RagBaseWorkstation() {
  const s = useHomeState();
  const location = useLocation();
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputToolbarRef = useRef<InputToolbarHandle>(null);
  const virtuosoRef = useRef<VirtuosoHandle>(null);
  const activeView = useMemo(() => pathToView(location.pathname), [location.pathname]);
  const isMobile = useIsMobile();
  const {
    isPageDragOver,
    handlePageDragOver,
    handlePageDragLeave,
    handlePageDrop,
  } = useDragAndDrop(inputToolbarRef);

  const navigateToView = useCallback(
    (view: ManageView) => navigate(viewToPath(view), { replace: false }),
    [navigate],
  );

  // 会话选中 → 输入框回填标题（原实现传空函数导致选中态从不回填）。
  const handleSetInputValue = useCallback(
    (value: string) => {
      inputToolbarRef.current?.setValue(value);
    },
    [inputToolbarRef],
  );

  useAutoScroll(virtuosoRef, s.displayMessages, s.activeConvId);

  // 移动端选中会话后自动收起抽屉（桌面端无此需求），防止遮罩覆盖消息区。
  const handleSetActiveConvId = useCallback(
    (id: string | null) => {
      navigateToView('chat');
      s.setActiveConvId(id);
      if (isMobile) s.setIsSidebarOpen(false);
    },
    [navigateToView, s.setActiveConvId, s.setIsSidebarOpen, isMobile],
  );

  const handleNewChat = useCallback(() => {
    navigateToView('chat');
    s.handleNewChat();
    if (isMobile) s.setIsSidebarOpen(false);
  }, [navigateToView, s.handleNewChat, s.setIsSidebarOpen, isMobile]);

  const handleToggleSidebar = useCallback(
    () => s.setIsSidebarOpen((prev) => !prev),
    [s.setIsSidebarOpen],
  );

  const handleCloseSidebar = useCallback(
    () => s.setIsSidebarOpen(false),
    [s.setIsSidebarOpen],
  );

  const handleCloseSettings = useCallback(
    () => s.setIsSettingsOpen(false),
    [s.setIsSettingsOpen],
  );

  const handleCloseApi = useCallback(
    () => s.setIsApiOpen(false),
    [s.setIsApiOpen],
  );

  const handleToggleTheme = useCallback(
    () => s.updateSettings({ theme: s.isDarkMode ? 'light' : 'dark' }),
    [s.updateSettings, s.isDarkMode],
  );

  return (
    <div className="h-dvh w-full flex flex-col overflow-hidden bg-[var(--color-surface)] text-[var(--color-text-secondary)]">
      <div className="flex flex-1 overflow-hidden relative">
        <RagBaseSidebar
          conversations={s.conversations}
          activeConvId={s.activeConvId}
          isUserMenuOpen={s.isUserMenuOpen}
          setIsUserMenuOpen={s.setIsUserMenuOpen}
          setIsSettingsOpen={s.setIsSettingsOpen}
          setIsApiOpen={s.setIsApiOpen}
          setActiveConvId={handleSetActiveConvId}
          setInputValue={handleSetInputValue}
          onDeleteConversation={s.handleDeleteConversation}
          onRenameConversation={s.handleRenameConversation}
          onPinConversation={s.handlePinConversation}
          onNewChat={handleNewChat}
          isSidebarOpen={s.isSidebarOpen}
          onToggleSidebar={handleToggleSidebar}
          isMobile={isMobile}
          onCloseSidebar={handleCloseSidebar}
          activeView={activeView}
          onNavigate={navigateToView}
        />

        <div className="flex flex-col flex-1 overflow-hidden">
          <WorkstationHeader
            isDarkMode={s.isDarkMode}
            onToggleTheme={handleToggleTheme}
            isSidebarOpen={s.isSidebarOpen}
            onToggleSidebar={handleToggleSidebar}
          />

          <main
            className={`flex-1 flex flex-col min-w-0 overflow-hidden relative bg-[var(--color-surface)] ${isPageDragOver ? 'ring-2 ring-inset ring-[var(--color-accent)]' : ''}`}
            id="main-content"
            onDragOver={handlePageDragOver}
            onDragLeave={handlePageDragLeave}
            onDrop={handlePageDrop}
          >
            {isPageDragOver && (
              <div className="fixed inset-0 flex items-center justify-center bg-[color-mix(in_srgb,var(--color-accent)_8%,var(--color-overlay))] border-[3px] border-dashed border-[var(--color-accent)] z-[900] text-xl font-bold text-[var(--color-accent)] pointer-events-none animate-[fadeIn_0.15s_ease]">
                <span>{s.t('fileAttach.dropHere')}</span>
              </div>
            )}
            {s.apiStatus === 'error' && s.apiError && (
              <div
                className="px-4 py-2 bg-[var(--color-danger)] text-[var(--color-text-on-accent)] text-center text-sm font-medium animate-[fadeIn_0.3s_ease] flex items-center justify-center gap-3"
                role="alert"
              >
                {s.apiError}
                <button
                  type="button"
                  className="bg-[var(--color-surface)] text-[var(--color-danger)] border-none py-px px-3 rounded text-sm cursor-pointer font-semibold leading-[1.6] hover:opacity-80"
                  onClick={() => void s.retryApi()}
                >
                  {s.t('common.retry')}
                </button>
              </div>
            )}
            {activeView === 'chat' ? (
              <div className="flex-1 flex flex-col overflow-hidden">
                <div className="flex-1 flex flex-col bg-[var(--color-surface)]">
                  {s.hasMessages ? (
                    <MessagesPanel
                      hasMessages={s.hasMessages}
                      displayMessages={s.displayMessages}
                      messagesEndRef={messagesEndRef}
                      onSwitchBranch={s.handleSwitchBranch}
                      virtuosoRef={virtuosoRef}
                    />
                  ) : (
                    <HomeScreen
                      conversationKey={0}
                      models={s.models}
                      selectedModel={s.selectedModel}
                      onModelChange={s.setSelectedModel}
                      commands={[]}
                      onSend={(text, files) => s.handleSend(text, files)}
                      onConfigureModels={() => s.setIsApiOpen(true)}
                      inputToolbarRef={inputToolbarRef}
                      isRunning={s.isRunning}
                      onStop={s.handleStop}
                    />
                  )}
                </div>

                {s.hasMessages && (
                  <InputToolbar
                    ref={inputToolbarRef}
                    onSend={(text, files) => s.handleSend(text, files)}
                    models={s.models}
                    selectedModel={s.selectedModel}
                    onModelChange={s.setSelectedModel}
                    placeholder={s.t('home.placeholder')}
                    commands={[]}
                    onConfigureModels={() => s.setIsApiOpen(true)}
                    isRunning={s.isRunning}
                    onStop={s.handleStop}
                  />
                )}
              </div>
            ) : (
              <div className="flex-1 overflow-hidden">
                <Suspense
                  fallback={
                    <div className="h-full flex items-center justify-center text-sm text-[var(--color-text-muted)]">
                      {s.t('common.loading')}
                    </div>
                  }
                >
                  {activeView === 'prompts' && <PromptLibraryPage />}
                  {activeView === 'assets' && <AssetsPage />}
                  {activeView === 'monitoring' && <QualityMonitor />}
                  {activeView === 'retrieval-logs' && <RetrievalLogPage />}
                  {activeView === 'admin-users' && <AdminUsersPage />}
                  {activeView === 'knowledge-bases' && <KnowledgeBasePage />}
                </Suspense>
              </div>
            )}
          </main>
        </div>
      </div>

      <Modals
        isSettingsOpen={s.isSettingsOpen}
        isApiOpen={s.isApiOpen}
        onCloseSettings={handleCloseSettings}
        onCloseApi={handleCloseApi}
      />
    </div>
  );
}
