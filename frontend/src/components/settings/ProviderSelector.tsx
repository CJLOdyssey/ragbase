import { useTranslation } from 'react-i18next';
import type { ProvidersMap } from '../../api/client/providers';
import { categoriesOf, CATEGORY_ORDER } from '../../utils/providerCategories';

interface Props {
  providers: ProvidersMap;
  providerType: string;
  onChangeProvider: (v: string) => void;
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
