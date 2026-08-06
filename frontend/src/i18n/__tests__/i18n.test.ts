import { describe, it, expect } from 'vitest';

function flattenKeys(obj: Record<string, unknown>, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([k, v]) => {
    const key = prefix ? `${prefix}.${k}` : k;
    return typeof v === 'object' && v !== null ? flattenKeys(v as Record<string, unknown>, key) : [key];
  });
}

async function loadLocale(lang: string): Promise<Record<string, unknown>> {
  const ns = ['common', 'sidebar', 'chat', 'workstation'];
  const result: Record<string, unknown> = {};
  for (const n of ns) {
    const mod = await import(`@/i18n/locales/${lang}/${n}.json`);
    Object.assign(result, mod.default);
  }
  return result;
}

describe('i18n', { tags: ['unit'] }, () => {
  it('zh-CN 和 en-US 的 key 集合一致', async () => {
    const zh = await loadLocale('zh-CN');
    const en = await loadLocale('en-US');

    const zhKeys = flattenKeys(zh).sort();
    const enKeys = flattenKeys(en).sort();

    const missing = zhKeys.filter((k) => !enKeys.includes(k));
    const extra = enKeys.filter((k) => !zhKeys.includes(k));

    expect(missing, `zh-CN missing: ${missing.join(', ')}`).toEqual([]);
    expect(extra, `en-US extra: ${extra.join(', ')}`).toEqual([]);
    expect(zhKeys.length).toBe(enKeys.length);
  });

  it('所有翻译值不为空', async () => {
    const zh = await loadLocale('zh-CN');
    const en = await loadLocale('en-US');

    const check = (obj: Record<string, unknown>, path = '') => {
      Object.entries(obj).forEach(([k, v]) => {
        const fullPath = path ? `${path}.${k}` : k;
        if (typeof v === 'string') {
          expect(v.trim(), `empty value at ${fullPath}`).not.toBe('');
        } else if (typeof v === 'object' && v !== null) {
          check(v as Record<string, unknown>, fullPath);
        }
      });
    };
    check(zh, 'zh-CN');
    check(en, 'en-US');
  });
});
