import {
  CAPABILITY_BADGE_KEYS,
  capabilityLabelKey,
  capabilityText,
  categoriesOf,
  CATEGORY_ORDER,
} from '../providerCategories';
import { describe, expect, it } from 'vitest';

describe('providerCategories', () => {
  it('orders all eight categories', () => {
    expect(CATEGORY_ORDER).toEqual([
      'llm',
      'embedding',
      'rerank',
      'speech2text',
      'tts',
      'moderation',
      'image',
      'tool',
    ]);
  });

  it('maps capabilities to categories', () => {
    expect(categoriesOf({ capabilities: ['chat'] })).toEqual(['llm']);
    expect(categoriesOf({ capabilities: ['vector'] })).toEqual(['embedding']);
    expect(categoriesOf({ capabilities: ['chat', 'vector', 'image'] })).toEqual(
      ['llm', 'embedding', 'image'],
    );
    expect(categoriesOf({ capabilities: ['tool'] })).toEqual(['tool']);
    expect(categoriesOf({ capabilities: ['image'] })).toEqual(['image']);
    expect(categoriesOf({ capabilities: [] })).toEqual([]);
    expect(categoriesOf({ capabilities: undefined })).toEqual([]);
  });

  it('maps remaining capability aliases to categories', () => {
    expect(categoriesOf({ capabilities: ['llm', 'embedding'] })).toEqual([
      'llm',
      'embedding',
    ]);
    expect(categoriesOf({ capabilities: ['rerank'] })).toEqual(['rerank']);
    expect(categoriesOf({ capabilities: ['speech2text'] })).toEqual([
      'speech2text',
    ]);
    expect(categoriesOf({ capabilities: ['tts'] })).toEqual(['tts']);
    expect(categoriesOf({ capabilities: ['moderation'] })).toEqual([
      'moderation',
    ]);
  });

  it('capabilityLabelKey wraps the category in a translation key', () => {
    expect(capabilityLabelKey('llm')).toBe('providerEdit.category.llm');
    expect(capabilityLabelKey('tool')).toBe('providerEdit.category.tool');
  });

  it('capabilityText maps known caps to badge keys and falls back', () => {
    expect(capabilityText('llm')).toBe(CAPABILITY_BADGE_KEYS.llm);
    expect(capabilityText('image')).toBe(CAPABILITY_BADGE_KEYS.image);
    expect(capabilityText('unknown-cap')).toBe(
      'providerEdit.badge.unknown-cap',
    );
  });
});
