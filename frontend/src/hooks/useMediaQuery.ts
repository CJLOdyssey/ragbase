import { useEffect, useState } from 'react';

/**
 * 响应式媒体查询 hook（受 theme/useResolvedTheme 影响，通用化）。
 * 用于需要按视口宽度分支渲染的组件（移动端抽屉等）。
 * 移动端断点与 Tailwind md (768px) 一致：<768px 视为移动端。
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(
    () => window.matchMedia(query).matches,
  );

  useEffect(() => {
    const mq = window.matchMedia(query);
    const onChange = () => setMatches(mq.matches);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [query]);

  return matches;
}

/** 是否为移动端视口（<768px，与 Tailwind md 断点一致）。 */
export function useIsMobile(): boolean {
  return useMediaQuery('(max-width: 767px)');
}
