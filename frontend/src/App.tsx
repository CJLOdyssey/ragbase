import { lazy, Suspense } from 'react';
import type * as React from 'react';
import { StyleProvider } from '@ant-design/cssinjs';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, theme } from 'antd';
import { ErrorBoundary, type FallbackProps } from 'react-error-boundary';
import { useTranslation } from 'react-i18next';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './components/auth/AuthContext';
import LoginModal from './components/auth/LoginModal';
import RagBaseWorkstation from './components/studio/RagBaseWorkstation';
import { useSettings } from './contexts/SettingsContext';
import { palette } from './theme/palette';
import { useResolvedIsDark } from './theme/useResolvedTheme';
import Logger from './utils/logger';
import { ToastProvider } from './utils/useToast';

const AssetsPage = lazy(() => import('./components/assets/AssetsPage'));
const PromptLibraryPage = lazy(
  () => import('./components/prompts/PromptLibraryPage'),
);
const QualityMonitor = lazy(
  () => import('./components/monitoring/QualityMonitor'),
);
const RetrievalLogPage = lazy(
  () => import('./components/retrieval-logs/RetrievalLogPage'),
);
const AdminUsersPage = lazy(() => import('./components/admin/AdminUsersPage'));
const KnowledgeBasePage = lazy(
  () => import('./components/knowledge-base/KnowledgeBasePage'),
);

function PageLoading() {
  const { t } = useTranslation();
  return (
    <div className="h-screen flex items-center justify-center text-sm text-[var(--color-text-muted)]">
      {t('common.loading')}
    </div>
  );
}

const CSS_VARS = {
  accent: '--color-accent',
} as const;

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 2, staleTime: 30_000, refetchOnWindowFocus: false },
  },
});

function Fallback({ error, resetErrorBoundary }: FallbackProps) {
  const { t } = useTranslation();
  const message = (error as Error)?.message || t('common.unknownError');
  Logger.error('React render error caught by ErrorBoundary', {
    error: error as Error,
  });

  return (
    <div
      className="flex flex-col items-center justify-center h-screen gap-4 p-8 text-center text-[var(--color-text-muted)]"
      role="alert"
    >
      <h2>{t('common.appError')}</h2>
      <p>{message}</p>
      <button
        className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-hover)] text-[var(--color-text-primary)] hover:bg-[var(--color-surface-elevated)] disabled:bg-[var(--color-surface-hover)] disabled:text-[var(--color-text-muted)] disabled:cursor-not-allowed"
        onClick={resetErrorBoundary}
      >
        {t('common.retry')}
      </button>
    </div>
  );
}

function logError(error: unknown) {
  Logger.error('App Error Boundary triggered', { error: error as Error });
}

function AppInit() {
  return null;
}

function AuthGate({ children }: { children: React.ReactNode }) {
  const { loginModalOpen, closeLoginModal } = useAuth();

  return (
    <>
      {children}
      {loginModalOpen && <LoginModal onClose={closeLoginModal} />}
    </>
  );
}

function getCssVar(name: string): string {
  if (typeof document === 'undefined') return '';
  return (
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() ||
    ''
  );
}

function ThemedApp() {
  const { settings } = useSettings();
  const { t } = useTranslation();
  // 令牌取自静态调色板（见 theme/palette.ts）——不能渲染期 getCssVar 读 DOM：
  // .dark class 在 effect 中翻转，渲染期读到的是上一次主题的值（竞态，
  // 曾导致弹窗配色不随主题切换）。accent 不随主题变，读 DOM 无竞态。
  const isDark = useResolvedIsDark(settings.theme);
  const colors = palette[isDark ? 'dark' : 'light'];
  const accentColor = getCssVar(CSS_VARS.accent) || '#6366f1';

  return (
    <StyleProvider layer={{ name: 'antd' } as unknown as boolean}>
      <ConfigProvider
        theme={{
          algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
          token: {
            colorPrimary: accentColor,
            colorBgContainer: colors.surface,
            colorBgElevated: colors.surfaceRaised,
            colorText: colors.textPrimary,
            colorTextSecondary: colors.textSecondary,
            colorBorder: colors.border,
            colorBgTextHover: colors.surfaceHover,
            borderRadius: 6,
            fontSize: 14,
          },
          components: {
            Button: {
              defaultBg: colors.surfaceRaised,
              colorBgContainer: colors.surfaceRaised,
            },
            Pagination: {
              itemBg: 'transparent',
              itemActiveBg: accentColor,
              itemInputBg: 'transparent',
            },
          },
        }}
      >
        <a
          className="skip-link"
          href="#main-content"
          style={{
            position: 'absolute',
            top: '-100%',
            left: 8,
            zIndex: 9999,
            padding: '8px 16px',
            background: accentColor,
            color: '#fff',
            borderRadius: '0 0 var(--radius-btn) var(--radius-btn)',
            fontSize: 14,
            textDecoration: 'none',
          }}
          onFocus={(e) => {
            (e.target as HTMLElement).style.top = '0';
          }}
          onBlur={(e) => {
            (e.target as HTMLElement).style.top = '-100%';
          }}
        >
          {t('common.skipToContent')}
        </a>
        <AuthProvider>
          <BrowserRouter>
            <ToastProvider>
              <AuthGate>
                <AppInit />
                <Routes>
                  <Route path="/" element={<RagBaseWorkstation />} />
                  <Route
                    path="/chat/:sessionId"
                    element={<RagBaseWorkstation />}
                  />
                  <Route
                    path="/prompts"
                    element={
                      <Suspense fallback={<PageLoading />}>
                        <PromptLibraryPage />
                      </Suspense>
                    }
                  />
                  <Route
                    path="/assets"
                    element={
                      <Suspense fallback={<PageLoading />}>
                        <AssetsPage />
                      </Suspense>
                    }
                  />
                  <Route
                    path="/monitoring"
                    element={
                      <Suspense fallback={<PageLoading />}>
                        <QualityMonitor />
                      </Suspense>
                    }
                  />
                  <Route
                    path="/retrieval-logs"
                    element={
                      <Suspense fallback={<PageLoading />}>
                        <RetrievalLogPage />
                      </Suspense>
                    }
                  />
                  <Route
                    path="/admin-users"
                    element={
                      <Suspense fallback={<PageLoading />}>
                        <AdminUsersPage />
                      </Suspense>
                    }
                  />
                  <Route
                    path="/knowledge-bases"
                    element={
                      <Suspense fallback={<PageLoading />}>
                        <KnowledgeBasePage />
                      </Suspense>
                    }
                  />
                  <Route
                    path="*"
                    element={
                      <ErrorBoundary
                        FallbackComponent={Fallback}
                        onError={logError}
                      >
                        <RagBaseWorkstation />
                      </ErrorBoundary>
                    }
                  />
                </Routes>
              </AuthGate>
            </ToastProvider>
          </BrowserRouter>
        </AuthProvider>
      </ConfigProvider>
    </StyleProvider>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemedApp />
    </QueryClientProvider>
  );
}
