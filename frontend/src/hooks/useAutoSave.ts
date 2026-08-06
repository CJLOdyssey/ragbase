import { useEffect, useRef } from 'react';
import { useSettings } from '../contexts/SettingsContext';

export function useAutoSave(key: string, data: unknown, enabled = true) {
  const { settings } = useSettings();
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (!settings.autoSave || !enabled) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      try {
        localStorage.setItem(key, JSON.stringify(data));
      } catch {
        /* empty */
      }
    }, 2000);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [data, key, settings.autoSave, enabled]);
}
