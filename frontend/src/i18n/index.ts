import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import adminEn from './locales/en-US/admin.json';
import apiEn from './locales/en-US/api.json';
import assetsEn from './locales/en-US/assets.json';
import commonEn from './locales/en-US/common.json';
import kbEn from './locales/en-US/knowledge-base.json';
import monitoringEn from './locales/en-US/monitoring.json';
import retrievalLogsEn from './locales/en-US/retrieval-logs.json';
import settingsEn from './locales/en-US/settings.json';
import adminZh from './locales/zh-CN/admin.json';
import apiZh from './locales/zh-CN/api.json';
import assetsZh from './locales/zh-CN/assets.json';
import commonZh from './locales/zh-CN/common.json';
import kbZh from './locales/zh-CN/knowledge-base.json';
import monitoringZh from './locales/zh-CN/monitoring.json';
import retrievalLogsZh from './locales/zh-CN/retrieval-logs.json';
import settingsZh from './locales/zh-CN/settings.json';

function deepMerge<T extends Record<string, unknown>>(
  target: T,
  ...sources: Partial<T>[]
): T {
  const out = { ...target };
  for (const src of sources) {
    for (const key of Object.keys(src) as (keyof T)[]) {
      const val = src[key];
      if (
        val &&
        typeof val === 'object' &&
        !Array.isArray(val) &&
        typeof out[key] === 'object' &&
        !Array.isArray(out[key])
      ) {
        out[key] = deepMerge(
          out[key] as Record<string, unknown>,
          val as Record<string, unknown>,
        ) as T[keyof T];
      } else if (val !== undefined) {
        out[key] = val as T[keyof T];
      }
    }
  }
  return out;
}

const zh = deepMerge(
  {},
  commonZh,
  apiZh,
  assetsZh,
  settingsZh,
  monitoringZh,
  kbZh,
  retrievalLogsZh,
  adminZh,
);
const en = deepMerge(
  {},
  commonEn,
  apiEn,
  assetsEn,
  settingsEn,
  monitoringEn,
  kbEn,
  retrievalLogsEn,
  adminEn,
);

// 存储不可用（隐私模式/SSR）时降级默认语言，模块初始化不抛错。
let saved: string | null = null;
if (typeof window !== 'undefined') {
  try {
    saved = localStorage.getItem('language');
  } catch {
    saved = null;
  }
}
const legacyMap: Record<string, string> = { en: 'en-US' };
const lang = saved ? legacyMap[saved] || saved : 'zh-CN';

const LANG_TO_HTML: Record<string, string> = {
  'zh-CN': 'zh-CN',
  'en-US': 'en',
};

void i18n.use(initReactI18next).init({
  resources: {
    'zh-CN': { translation: zh },
    'en-US': { translation: en },
  },
  lng: lang,
  fallbackLng: 'zh-CN',
  interpolation: {
    escapeValue: false,
    prefix: '{{',
    suffix: '}}',
  },
});

if (typeof document !== 'undefined') {
  document.documentElement.lang = LANG_TO_HTML[i18n.language] || i18n.language;
}

export function changeLanguage(lng: string) {
  try {
    localStorage.setItem('language', lng);
  } catch {
    // storage unavailable — session-only language switch
  }
  void i18n.changeLanguage(lng);
  if (typeof document !== 'undefined') {
    document.documentElement.lang = LANG_TO_HTML[lng] || lng;
  }
}

export function getCurrentLanguage(): string {
  return i18n.language;
}

export default i18n;
