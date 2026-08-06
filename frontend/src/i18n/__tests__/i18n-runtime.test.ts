import { describe, it, expect, beforeEach } from 'vitest';
import { changeLanguage, getCurrentLanguage } from '@/i18n/index';

describe('i18n runtime', { tags: ['unit'] }, () => {
  beforeEach(() => {
    document.documentElement.lang = '';
  });

  it('getCurrentLanguage returns current language', () => {
    const lang = getCurrentLanguage();
    expect(lang).toBeDefined();
    expect(['zh-CN', 'en-US']).toContain(lang);
  });

  it('changeLanguage to en-US updates localStorage and document', () => {
    changeLanguage('en-US');
    expect(localStorage.getItem('language')).toBe('en-US');
    expect(document.documentElement.lang).toBe('en');
  });

  it('changeLanguage to zh-CN updates localStorage and document', () => {
    changeLanguage('zh-CN');
    expect(localStorage.getItem('language')).toBe('zh-CN');
    expect(document.documentElement.lang).toBe('zh-CN');
  });

  it('changeLanguage handles unknown language code', () => {
    changeLanguage('fr-FR');
    expect(localStorage.getItem('language')).toBe('fr-FR');
    expect(document.documentElement.lang).toBe('fr-FR');
  });
});
