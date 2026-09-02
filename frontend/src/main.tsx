import React from 'react';
import ReactDOM from 'react-dom/client';
import * as Sentry from '@sentry/react';
import App from './App';
import { SettingsProvider } from './contexts/SettingsContext';
import { installGlobalErrorHandlers } from './utils/errorHandler';
import { getStorageManager } from './utils/storage';
import './i18n/index';
import './styles/tailwind-entry.css';
import './styles/modals/index.css';
import './styles/antd/index.css';

// 验证 localStorage 旧数据
getStorageManager().validateAll();

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN || '',
  environment: import.meta.env.MODE,
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration(),
  ],
  tracesSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  enabled: !!import.meta.env.VITE_SENTRY_DSN,
});

installGlobalErrorHandlers();

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    void navigator.serviceWorker.register('/sw.js');
  });
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <Sentry.ErrorBoundary fallback={<p>An error has occurred</p>} showDialog>
    <React.StrictMode>
      <SettingsProvider>
        <App />
      </SettingsProvider>
    </React.StrictMode>
  </Sentry.ErrorBoundary>,
);
