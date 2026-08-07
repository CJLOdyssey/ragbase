import {
  SettingsProvider,
  useNotificationSound,
  useSettings,
} from '@/contexts/SettingsContext';
import { act, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

function TestConsumer({
  onRender,
}: {
  onRender?: (s: ReturnType<typeof useSettings>) => void;
}) {
  const settings = useSettings();
  onRender?.(settings);
  return (
    <div>
      <span data-testid="theme">{settings.settings.theme}</span>
      <span data-testid="fontSize">{settings.settings.fontSize}</span>
      <span data-testid="sendMode">{settings.settings.sendMode}</span>
      <span data-testid="autoSave">{String(settings.settings.autoSave)}</span>
      <span data-testid="streamOutput">
        {String(settings.settings.streamOutput)}
      </span>
    </div>
  );
}

describe('SettingsContext', { tags: ['unit'] }, () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
    document.documentElement.style.removeProperty('--body-font-size');
  });

  it('renders with default settings', () => {
    render(
      <SettingsProvider>
        <TestConsumer />
      </SettingsProvider>,
    );
    expect(screen.getByTestId('theme').textContent).toBe('dark');
    expect(screen.getByTestId('fontSize').textContent).toBe('16');
    expect(screen.getByTestId('sendMode').textContent).toBe('enter');
    expect(screen.getByTestId('autoSave').textContent).toBe('true');
    expect(screen.getByTestId('streamOutput').textContent).toBe('true');
  });

  it('applies dark theme class on mount', () => {
    render(
      <SettingsProvider>
        <TestConsumer />
      </SettingsProvider>,
    );
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('sets font size CSS variable on mount', () => {
    render(
      <SettingsProvider>
        <TestConsumer />
      </SettingsProvider>,
    );
    expect(
      document.documentElement.style.getPropertyValue('--body-font-size'),
    ).toBe('16px');
  });

  it('loads settings from localStorage', () => {
    localStorage.setItem(
      'ragbase-settings',
      JSON.stringify({ theme: 'light', fontSize: 18, sendMode: 'ctrl-enter' }),
    );
    render(
      <SettingsProvider>
        <TestConsumer />
      </SettingsProvider>,
    );
    expect(screen.getByTestId('theme').textContent).toBe('light');
    expect(screen.getByTestId('fontSize').textContent).toBe('18');
    expect(screen.getByTestId('sendMode').textContent).toBe('ctrl-enter');
  });

  it('persists settings to localStorage on update', () => {
    let settings!: ReturnType<typeof useSettings>;
    render(
      <SettingsProvider>
        <TestConsumer
          onRender={(s) => {
            settings = s;
          }}
        />
      </SettingsProvider>,
    );
    act(() => {
      settings.updateSettings({ theme: 'light', fontSize: 20 });
    });
    const saved = JSON.parse(localStorage.getItem('ragbase-settings') || '{}');
    expect(saved.theme).toBe('light');
    expect(saved.fontSize).toBe(20);
  });

  it('handles corrupted localStorage gracefully', () => {
    localStorage.setItem('ragbase-settings', 'invalid-json{{{');
    render(
      <SettingsProvider>
        <TestConsumer />
      </SettingsProvider>,
    );
    // Should fall back to defaults
    expect(screen.getByTestId('theme').textContent).toBe('dark');
  });

  it('switches theme from dark to light', () => {
    let settings!: ReturnType<typeof useSettings>;
    render(
      <SettingsProvider>
        <TestConsumer
          onRender={(s) => {
            settings = s;
          }}
        />
      </SettingsProvider>,
    );
    act(() => {
      settings.updateSettings({ theme: 'light' });
    });
    expect(screen.getByTestId('theme').textContent).toBe('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('handles system theme preference', () => {
    let settings!: ReturnType<typeof useSettings>;
    render(
      <SettingsProvider>
        <TestConsumer
          onRender={(s) => {
            settings = s;
          }}
        />
      </SettingsProvider>,
    );
    act(() => {
      settings.updateSettings({ theme: 'system' });
    });
    expect(screen.getByTestId('theme').textContent).toBe('system');
  });

  describe('useNotificationSound', () => {
    it('returns a function', () => {
      function SoundConsumer() {
        const play = useNotificationSound();
        return <span data-testid="play-type">{typeof play}</span>;
      }
      render(
        <SettingsProvider>
          <SoundConsumer />
        </SettingsProvider>,
      );
      expect(screen.getByTestId('play-type').textContent).toBe('function');
    });

    it('does not throw when called', () => {
      function SoundConsumer() {
        const play = useNotificationSound();
        return <button onClick={() => play()}>Beep</button>;
      }
      render(
        <SettingsProvider>
          <SoundConsumer />
        </SettingsProvider>,
      );
      act(() => {
        screen.getByText('Beep').click();
      });
    });
  });

  describe('useSettings error boundary', () => {
    it('throws when used outside SettingsProvider', () => {
      function BadConsumer() {
        useSettings();
        return null;
      }
      expect(() => render(<BadConsumer />)).toThrow(
        'useSettings must be used within SettingsProvider',
      );
    });
  });
});
