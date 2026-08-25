import { useEffect, useState } from 'react';
import type { Theme } from '../contexts/SettingsContext';

function useSystemPrefersDark(active: boolean): boolean {
  const [systemDark, setSystemDark] = useState(
    () => window.matchMedia('(prefers-color-scheme: dark)').matches,
  );

  useEffect(() => {
    if (!active) return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => setSystemDark(mq.matches);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [active]);

  return systemDark;
}

// settings.theme === 'system' 时跟随操作系统；此前各处用
// `theme === 'dark'` 判断，system + 深色系统会被当成亮色。
export function useResolvedIsDark(theme: Theme): boolean {
  const systemDark = useSystemPrefersDark(theme === 'system');
  return theme === 'dark' || (theme === 'system' && systemDark);
}
