import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { STORAGE_KEYS } from '../utils/storage';

export type Theme = 'dark' | 'light' | 'system';

interface Settings {
  theme: Theme;
  fontSize: number;
  sendMode: 'enter' | 'ctrl-enter';
  autoSave: boolean;
  streamOutput: boolean;
}

interface SettingsContextType {
  settings: Settings;
  updateSettings: (updates: Partial<Settings>) => void;
}

const defaultSettings: Settings = {
  theme: 'dark',
  fontSize: 16,
  sendMode: 'enter',
  autoSave: true,
  streamOutput: true,
};

const SettingsContext = createContext<SettingsContextType | undefined>(
  undefined,
);

function playBeep() {
  try {
    // WebAudio API 在无头浏览器/隐私模式下不可用——音效失败不阻塞 UI。
    const AudioCtor =
      window.AudioContext ||
      (window as { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;
    const ctx = new AudioCtor!();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 660;
    gain.gain.value = 0.08;
    osc.start();
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);
    osc.stop(ctx.currentTime + 0.15);
  } catch {
    // 音效为非关键功能：失败降级为静默，不向上抛出
  }
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.SETTINGS);
      return saved
        ? { ...defaultSettings, ...JSON.parse(saved) }
        : defaultSettings;
    } catch {
      return defaultSettings;
    }
  });

  useEffect(() => {
    // 与读取同等的降级保护：隐私模式/配额满时写失败不抛异常
    // （设置仅在内存生效，刷新后回默认）。
    try {
      localStorage.setItem(STORAGE_KEYS.SETTINGS, JSON.stringify(settings));
    } catch {
      // storage unavailable — in-memory settings still apply
    }
  }, [settings]);

  useEffect(() => {
    document.documentElement.style.setProperty(
      '--body-font-size',
      `${settings.fontSize}px`,
    );
  }, [settings.fontSize]);

  useEffect(() => {
    const root = document.documentElement;
    const setThemeClass = (theme: Theme) => {
      root.classList.remove('dark');
      if (theme === 'dark') root.classList.add('dark');
      else if (theme === 'system') {
        if (window.matchMedia('(prefers-color-scheme: dark)').matches)
          root.classList.add('dark');
      }
    };
    const applyTheme = () => {
      if (document.startViewTransition) {
        document.startViewTransition(() => setThemeClass(settings.theme));
      } else {
        setThemeClass(settings.theme);
      }
    };
    applyTheme();

    if (settings.theme === 'system') {
      const mq = window.matchMedia('(prefers-color-scheme: dark)');
      const onChange = () => setThemeClass('system');
      mq.addEventListener('change', onChange);
      return () => {
        mq.removeEventListener('change', onChange);
      };
    }
  }, [settings.theme]);

  const updateSettings = (updates: Partial<Settings>) => {
    setSettings((prev) => ({ ...prev, ...updates }));
  };

  return (
    <SettingsContext.Provider value={{ settings, updateSettings }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error('useSettings must be used within SettingsProvider');
  return ctx;
}

export function useNotificationSound() {
  return useCallback(() => {
    playBeep();
  }, []);
}
