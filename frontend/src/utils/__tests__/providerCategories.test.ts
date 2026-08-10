import { categoriesOf, CATEGORY_ORDER } from '../providerCategories';
import { describe, expect, it } from 'vitest';

describe('providerCategories', () => {
  it('orders all seven categories', () => {
    expect(CATEGORY_ORDER).toEqual([
      'llm',
      'embedding',
      'rerank',
      'speech2text',
      'tts',
      'moderation',
      'tool',
    ]);
  });

  it('maps capabilities to categories', () => {
    expect(categoriesOf({ capabilities: ['chat'] })).toEqual(['llm']);
    expect(categoriesOf({ capabilities: ['vector'] })).toEqual(['embedding']);
    expect(categoriesOf({ capabilities: ['chat', 'vector', 'image'] })).toEqual(
      ['llm', 'embedding', 'tool'],
    );
    expect(categoriesOf({ capabilities: ['tool'] })).toEqual(['tool']);
    expect(categoriesOf({ capabilities: [] })).toEqual([]);
    expect(categoriesOf({ capabilities: undefined })).toEqual([]);
  });
});
