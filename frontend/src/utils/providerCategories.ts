export const CATEGORY_ORDER = [
  'llm',
  'embedding',
  'rerank',
  'speech2text',
  'tts',
  'moderation',
  'image',
  'tool',
] as const;

export type Category = (typeof CATEGORY_ORDER)[number];

// 徽章文案映射：capability → 用途徽章 i18n key
export const CAPABILITY_BADGE_KEYS: Record<string, string> = {
  llm: 'providerEdit.badge.llm',
  embedding: 'providerEdit.badge.embedding',
  rerank: 'providerEdit.badge.rerank',
  speech2text: 'providerEdit.badge.speech2text',
  tts: 'providerEdit.badge.tts',
  moderation: 'providerEdit.badge.moderation',
  image: 'providerEdit.badge.image',
  tool: 'providerEdit.badge.tool',
};

export function categoriesOf(info: { capabilities?: string[] }): Category[] {
  const caps = info.capabilities ?? [];
  const cats: Category[] = [];
  if (caps.includes('chat') || caps.includes('llm')) cats.push('llm');
  if (caps.includes('vector') || caps.includes('embedding'))
    cats.push('embedding');
  if (caps.includes('rerank')) cats.push('rerank');
  if (caps.includes('speech2text')) cats.push('speech2text');
  if (caps.includes('tts')) cats.push('tts');
  if (caps.includes('moderation')) cats.push('moderation');
  if (caps.includes('image')) cats.push('image');
  if (caps.includes('tool')) cats.push('tool');
  return cats;
}

export function capabilityLabelKey(cat: Category): string {
  return `providerEdit.category.${cat}`;
}

export function capabilityText(cap: string): string {
  return CAPABILITY_BADGE_KEYS[cap] ?? `providerEdit.badge.${cap}`;
}
