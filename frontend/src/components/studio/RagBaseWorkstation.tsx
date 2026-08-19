import { lazy, Suspense, useRef, useState } from 'react';
import InputToolbar, { type InputToolbarHandle } from '../input/InputToolbar';
import HomeScreen from './HomeScreen';
import MessagesPanel from './MessagesPanel';
import Modals from './Modals';
import RagBaseSidebar from './RagBaseSidebar';
import WorkstationHeader from './WorkstationHeader';
import { useAutoScroll } from './useAutoScroll';
import { useDragAndDrop } from './useDragAndDrop';
import { useHomeState } from './useHomeState';

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
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputToolbarRef = useRef<InputToolbarHandle>(null);
  const [activeView, setActiveView] = useState<ManageView>('chat');
  const {
    isPageDragOver,
    handlePageDragOver,
    handlePageDragLeave,
    handlePageDrop,
  } = useDragAndDrop(inputToolbarRef);

  useAutoScroll(messagesContainerRef, s.displayMessages, s.activeConvId);

  return (
    <div className="h-screen w-full flex flex-col overflow-hidden bg-[var(--color-surface)] text-[var(--color-text-secondary)]">
      <div className="flex flex-1 overflow-hidden relative">
        <RagBaseSidebar
          conversations={s.conversations}
          activeConvId={s.activeConvId}
          isUserMenuOpen={s.isUserMenuOpen}
          setIsUserMenuOpen={s.setIsUserMenuOpen}
          setIsSettingsOpen={s.setIsSettingsOpen}
          setIsApiOpen={s.setIsApiOpen}
          setActiveConvId={(id) => {
            setActiveView('chat');
            s.setActiveConvId(id);
          }}
          setInputValue={() => {}}
          onDeleteConversation={s.handleDeleteConversation}
          onRenameConversation={s.handleRenameConversation}
          onPinConversation={s.handlePinConversation}
          onNewChat={() => {
            setActiveView('chat');
            s.handleNewChat();
          }}
          isSidebarOpen={s.isSidebarOpen}
          onToggleSidebar={() => s.setIsSidebarOpen(false)}
          activeView={activeView}
          onNavigate={setActiveView}
        />

        <div className="flex flex-col flex-1 overflow-hidden">
          <WorkstationHeader
            isDarkMode={s.isDarkMode}
            onToggleTheme={() =>
              s.updateSettings({
                theme: s.isDarkMode ? 'light' : 'dark',
              })
            }
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
                <div
                  className="flex-1 overflow-y-auto flex flex-col bg-[var(--color-surface)]"
                  ref={messagesContainerRef}
                >
                  {s.hasMessages ? (
                    <MessagesPanel
                      hasMessages={s.hasMessages}
                      displayMessages={s.displayMessages}
                      messagesEndRef={messagesEndRef}
                      onSwitchBranch={s.handleSwitchBranch}
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
        onCloseSettings={() => s.setIsSettingsOpen(false)}
        onCloseApi={() => s.setIsApiOpen(false)}
      />
    </div>
  );
}
