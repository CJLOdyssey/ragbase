import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import commonZh from './locales/zh-CN/common.json';
import sidebarZh from './locales/zh-CN/sidebar.json';
import chatZh from './locales/zh-CN/chat.json';
import workstationZh from './locales/zh-CN/workstation.json';
import apiZh from './locales/zh-CN/api.json';

import commonEn from './locales/en-US/common.json';
import sidebarEn from './locales/en-US/sidebar.json';
import chatEn from './locales/en-US/chat.json';
import workstationEn from './locales/en-US/workstation.json';
import apiEn from './locales/en-US/api.json';

function deepMerge<T extends Record<string, unknown>>(target: T, ...sources: Partial<T>[]): T {
  const out = { ...target };
  for (const src of sources) {
    for (const key of Object.keys(src) as (keyof T)[]) {
      const val = src[key];
      if (val && typeof val === 'object' && !Array.isArray(val) && typeof out[key] === 'object' && !Array.isArray(out[key])) {
        out[key] = deepMerge(out[key] as Record<string, unknown>, val as Record<string, unknown>) as T[keyof T];
      } else if (val !== undefined) {
        out[key] = val as T[keyof T];
      }
    }
  }
  return out;
}

const zh = deepMerge({}, commonZh, sidebarZh, chatZh, workstationZh, apiZh);
const en = deepMerge({}, commonEn, sidebarEn, chatEn, workstationEn, apiEn);

const saved = typeof window !== 'undefined' ? localStorage.getItem('language') : null;
const legacyMap: Record<string, string> = { en: 'en-US' };
const lang = saved ? (legacyMap[saved] || saved) : 'zh-CN';

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
