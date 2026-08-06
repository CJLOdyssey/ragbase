import * as logger from './logger';

export function installGlobalErrorHandlers() {
  if (typeof window === 'undefined') return;

  window.onerror = (message, source, lineno, colno, error) => {
    logger.error('Uncaught error', { message, source, lineno, colno, error });
    return false;
  };

  window.onunhandledrejection = (event) => {
    const reason = event.reason;
    const msg = reason?.message || '';
    if (msg.startsWith('Transition was skipped') || msg.startsWith('Transition was aborted')) {
      event.preventDefault();
      return;
    }
    logger.error('Unhandled promise rejection', { reason });
  };
}
