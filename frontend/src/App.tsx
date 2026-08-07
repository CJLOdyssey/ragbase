import { lazy, Suspense } from 'react';
import type * as React from 'react';
import { StyleProvider } from '@ant-design/cssinjs';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, theme } from 'antd';
import { ErrorBoundary, type FallbackProps } from 'react-error-boundary';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider, LoginModal, useAuth } from './components/auth';
import RagBaseWorkstation from './components/studio/RagBaseWorkstation';
import { useSettings } from './contexts/SettingsContext';
import Logger from './utils/logger';
import { ToastProvider } from './utils/useToast';

const AssetsPage = lazy(() => import('./components/assets/AssetsPage'));
const SettingsPage = lazy(() => import('./components/settings/SettingsPage'));

function PageLoading() {
  return (
    <div className="h-screen flex items-center justify-center text-sm text-[var(--color-text-muted)]">
      加载中…
    </div>
  );
}

const CSS_VARS = {
  accent: '--color-accent',
  surface: '--color-surface',
  surfaceRaised: '--color-surface-raised',
  textPrimary: '--color-text-primary',
  textSecondary: '--color-text-secondary',
  border: '--color-border',
  surfaceHover: '--color-surface-hover',
} as const;

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 2, staleTime: 30_000, refetchOnWindowFocus: false },
  },
});

function Fallback({ error, resetErrorBoundary }: FallbackProps) {
  const message = (error as Error)?.message || '未知错误';
  Logger.error('React render error caught by ErrorBoundary', {
    error: error as Error,
  });

  return (
    <div
      className="flex flex-col items-center justify-center h-screen gap-4 p-8 text-center text-[var(--color-text-muted)]"
      role="alert"
    >
      <h2>应用出错了</h2>
      <p>{message}</p>
      <button
        className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-hover)] text-[var(--color-text-primary)] hover:bg-[var(--color-surface-elevated)] disabled:bg-[var(--color-surface-hover)] disabled:text-[var(--color-text-muted)] disabled:cursor-not-allowed"
        onClick={resetErrorBoundary}
      >
        重试
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
  const isDark = settings.theme === 'dark';
  const bgColor =
    getCssVar(CSS_VARS.surface) || (isDark ? '#0f1117' : '#ffffff');
  const bgElevated =
    getCssVar(CSS_VARS.surfaceRaised) || (isDark ? '#1c1e24' : '#f7f8fa');
  const txtColor =
    getCssVar(CSS_VARS.textPrimary) || (isDark ? '#f1f1f1' : '#1a1a2e');
  const txtSecondary =
    getCssVar(CSS_VARS.textSecondary) || (isDark ? '#a0a5b0' : '#495057');
  const borderColor =
    getCssVar(CSS_VARS.border) ||
    (isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)');
  const surfaceHover =
    getCssVar(CSS_VARS.surfaceHover) ||
    (isDark ? 'rgba(255,255,255,0.08)' : '#f1f3f5');
  const accentColor = getCssVar(CSS_VARS.accent) || '#6366f1';

  return (
    <StyleProvider layer={{ name: 'antd' } as unknown as boolean}>
      <ConfigProvider
        theme={{
          algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
          token: {
            colorPrimary: accentColor,
            colorBgContainer: bgColor,
            colorBgElevated: bgElevated,
            colorText: txtColor,
            colorTextSecondary: txtSecondary,
            colorBorder: borderColor,
            colorBgTextHover: surfaceHover,
            borderRadius: 6,
            fontSize: 14,
          },
          components: {
            Button: {
              defaultBg: bgElevated,
              colorBgContainer: bgElevated,
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
          跳转到主内容
        </a>
        <AuthProvider>
          <BrowserRouter
            future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          >
            <ToastProvider>
              <AuthGate>
                <AppInit />
                <Routes>
                  <Route path="/" element={<RagBaseWorkstation />} />
                  <Route
                    path="/assets"
                    element={
                      <Suspense fallback={<PageLoading />}>
                        <AssetsPage />
                      </Suspense>
                    }
                  />
                  <Route
                    path="/settings"
                    element={
                      <Suspense fallback={<PageLoading />}>
                        <SettingsPage />
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
