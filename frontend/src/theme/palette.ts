// antd ConfigProvider 令牌调色板 —— 唯一事实源。
// 必须与 styles/tailwind-entry.css 的 :root（暗色）/ :root:not(.dark)（亮色）保持同步；
// 改色时两处一起改。不能在渲染期用 getCssVar 读 DOM 取色：
// .dark class 在 effect 中翻转，渲染期读到的是上一次主题的值（竞态）。
export type ThemeMode = 'dark' | 'light';

export interface ThemePalette {
  surface: string;
  surfaceRaised: string;
  textPrimary: string;
  textSecondary: string;
  border: string;
  surfaceHover: string;
}

export const palette: Record<ThemeMode, ThemePalette> = {
  dark: {
    surface: '#0f1117',
    surfaceRaised: '#1c1e24',
    textPrimary: '#f1f1f1',
    textSecondary: '#a0a5b0',
    border: 'rgba(255, 255, 255, 0.12)',
    surfaceHover: 'rgba(255, 255, 255, 0.08)',
  },
  light: {
    surface: '#ffffff',
    surfaceRaised: '#f7f8fa',
    textPrimary: '#1a1a2e',
    textSecondary: '#495057',
    border: 'rgba(0, 0, 0, 0.08)',
    surfaceHover: '#f1f3f5',
  },
};
