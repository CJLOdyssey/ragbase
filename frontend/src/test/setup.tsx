import '@testing-library/jest-dom';
import * as axeMatchers from 'vitest-axe/matchers';
import { vi, expect } from 'vitest';

expect.extend(axeMatchers);

// Suppress act(...) warnings from harmless async effects (useGenericCrud,
// usePickerState, etc.). These are noisy but harmless when tests pass.
const _origWarn = console.warn;
const _origErr = console.error;
console.warn = (...args: unknown[]) => {
  if (typeof args[0] === 'string' && args[0].includes('not wrapped in act')) return;
  _origWarn.call(console, ...args);
};
console.error = (...args: unknown[]) => {
  if (typeof args[0] === 'string' && args[0].includes('not wrapped in act')) return;
  _origErr.call(console, ...args);
};
import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { VirtuosoMockContext } from 'react-virtuoso';
import { SettingsProvider } from '../contexts/SettingsContext';
import { ToastProvider } from '../utils/useToast';
import '../i18n/index';

vi.mock('../components/auth', () => ({
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  useAuth: () => ({
    user: null,
    loading: false,
    legacyMode: false,
    isAuthenticated: false,
    loginModalOpen: false,
    loginModalView: 'login' as const,
    loginModalEmail: '',
    login: vi.fn(),
    register: vi.fn(),
    verify: vi.fn(),
    forgotPassword: vi.fn(),
    resetPassword: vi.fn(),
    logout: vi.fn(),
    resendVerification: vi.fn(),
    sendRegisterCode: vi.fn(),
    openLoginModal: vi.fn(),
    closeLoginModal: vi.fn(),
    setLoginModalEmail: vi.fn(),
    refetchUser: vi.fn(),
  }),
}));

Element.prototype.scrollIntoView = vi.fn();
Element.prototype.scrollTo = vi.fn();
Object.defineProperty(window, 'matchMedia', { writable: true, value: vi.fn().mockImplementation((query: string) => ({ matches: false, media: query, onchange: null, addListener: vi.fn(), removeListener: vi.fn(), addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn() })) });

// react-virtuoso requires ResizeObserver to measure container dimensions
window.ResizeObserver = vi.fn(function ResizeObserver(callback: ResizeObserverCallback) {
  const targets = new WeakSet<Element>();
  return {
    observe(target: Element) {
      targets.add(target);
      Promise.resolve().then(() => {
        const width = parseFloat((target as HTMLElement).style.width) || 800;
        const height = parseFloat((target as HTMLElement).style.height) || 600;
        callback(
          [{ borderBoxSize: [{ blockSize: height, inlineSize: width }], contentBoxSize: [{ blockSize: height, inlineSize: width }], contentRect: new DOMRectReadOnly(0, 0, width, height), devicePixelContentBoxSize: [{ blockSize: height, inlineSize: width }], target }],
          this as unknown as ResizeObserver,
        );
      });
    },
    unobserve(target: Element) { targets.delete(target); },
    disconnect() {},
  } as unknown as ResizeObserver;
});

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

export function TestProviders({ children }: { children: ReactNode }) {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <SettingsProvider>
        <ToastProvider>
          <VirtuosoMockContext.Provider value={{ viewportHeight: 800, itemHeight: 60 }}>
            {children}
          </VirtuosoMockContext.Provider>
        </ToastProvider>
      </SettingsProvider>
    </QueryClientProvider>
  );
}
