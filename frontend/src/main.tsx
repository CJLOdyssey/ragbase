import React from 'react';
import ReactDOM from 'react-dom/client';
import * as Sentry from '@sentry/react';
import App from './App';
import { SettingsProvider } from './contexts/SettingsContext';
import { installGlobalErrorHandlers } from './utils/errorHandler';
import './i18n/index';
import './styles/tailwind-entry.css';
import './styles/modals/index.css';
import './styles/antd/index.css';

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN || '',
  environment: import.meta.env.MODE,
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration(),
  ],
  // Performance Monitoring
  tracesSampleRate: 1.0, // Capture 100% of transactions in dev; reduce in prod
  // Session Replay
  replaysSessionSampleRate: 0.1, // 10% of sessions
  replaysOnErrorSampleRate: 1.0, // 100% of error sessions
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
