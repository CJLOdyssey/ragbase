import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import apiEn from './locales/en-US/api.json';
import assetsEn from './locales/en-US/assets.json';
import commonEn from './locales/en-US/common.json';
import monitoringEn from './locales/en-US/monitoring.json';
import settingsEn from './locales/en-US/settings.json';
import apiZh from './locales/zh-CN/api.json';
import assetsZh from './locales/zh-CN/assets.json';
import commonZh from './locales/zh-CN/common.json';
import monitoringZh from './locales/zh-CN/monitoring.json';
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

const zh = deepMerge({}, commonZh, apiZh, assetsZh, settingsZh, monitoringZh);
const en = deepMerge({}, commonEn, apiEn, assetsEn, settingsEn, monitoringEn);

const saved =
  typeof window !== 'undefined' ? localStorage.getItem('language') : null;
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
  localStorage.setItem('language', lng);
  void i18n.changeLanguage(lng);
  if (typeof document !== 'undefined') {
    document.documentElement.lang = LANG_TO_HTML[lng] || lng;
  }
}

export function getCurrentLanguage(): string {
  return i18n.language;
}

export default i18n;
