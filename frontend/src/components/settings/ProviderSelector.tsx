import { useTranslation } from 'react-i18next';
import type { ProvidersMap } from '../../api/client/providers';

interface Props {
  providers: ProvidersMap;
  providerType: string;
  onChangeProvider: (v: string) => void;
}

// 供应商按能力类型分组（对齐 Dify ModelType 全量 + AstrBot 能力枚举）。
// 图像生成按 Dify 惯例归入工具类（Dify 中 DALL-E/Flux 等图像工具即 Tool 插件）；
// 一个供应商可有多个能力类型，可同时出现在多个组；
// 暂无供应商的模型类型组保留定义，有供应商时自动显示（无需改代码）。
const CATEGORY_ORDER = [
  'llm',
  'embedding',
  'rerank',
  'speech2text',
  'tts',
  'moderation',
  'tool',
] as const;
type Category = (typeof CATEGORY_ORDER)[number];

function categoriesOf(info: { capabilities?: string[] }): Category[] {
  const caps = info.capabilities ?? [];
  const cats: Category[] = [];
  if (caps.includes('chat')) cats.push('llm');
  if (caps.includes('vector')) cats.push('embedding');
  if (caps.includes('rerank')) cats.push('rerank');
  if (caps.includes('speech2text')) cats.push('speech2text');
  if (caps.includes('tts')) cats.push('tts');
  if (caps.includes('moderation')) cats.push('moderation');
  if (caps.includes('tool') || caps.includes('image')) cats.push('tool');
  return cats;
}

export default function ProviderSelector({
  providers,
  providerType,
  onChangeProvider,
}: Props) {
  const { t } = useTranslation();

  const groups = CATEGORY_ORDER.map((cat) => ({
    cat,
    items: Object.entries(providers).filter(
      // 自定义无条件进入所有组：每类能力均可自定义接入；空组因 custom 而可见可用。
      ([key, info]) => key === 'custom' || categoriesOf(info).includes(cat),
    ),
  })).filter((g) => g.items.length > 0);

  return (
    <div>
      <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">
        {t('providerEdit.provider')}
      </label>
      <select
        value={providerType}
        onChange={(e) => onChangeProvider(e.target.value)}
        className="w-full py-2 pr-7 pl-3 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-md text-[var(--color-text-primary)] text-sm font-sans outline-none cursor-pointer transition-colors appearance-none focus:border-[var(--color-accent)] focus:shadow-[0 0 0 2px var(--color-accent)]"
      >
        {groups.map(({ cat, items }) => (
          <optgroup key={cat} label={t(`providerEdit.category.${cat}`)}>
            {items.map(([key, info]) => (
              <option key={key} value={key}>
                {info.name}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  );
}
