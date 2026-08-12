import { Loader2, RefreshCw, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CATEGORY_ORDER } from '../../utils/providerCategories';

interface Props {
  models: string[];
  modelTypes: Record<string, string>;
  /** Inferred type fallbacks (from /api/models) for models without an explicit stored type. */
  typeDefaults?: Record<string, string>;
  fetching: boolean;
  apiKey: string;
  onRemoveModel: (model: string) => void;
  onFetchModels: () => void;
  onChangeModelType: (model: string, type: string) => void;
}

export default function ModelSection({
  models,
  modelTypes,
  typeDefaults = {},
  fetching,
  apiKey,
  onRemoveModel,
  onFetchModels,
  onChangeModelType,
}: Props) {
  const { t } = useTranslation();

  return (
    <div>
      <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">
        {t('providerEdit.supportedModels')}
      </label>
      <div className="flex items-start gap-2">
        {models.length > 0 ? (
          <div className="flex-1 flex flex-col gap-1.5 p-2 bg-[var(--color-surface-elevated)] border border-[var(--color-border)] rounded-md min-h-[36px] max-h-[84px] overflow-y-auto">
            {models.map((model) => (
              <div
                key={model}
                className="flex items-center gap-2 px-2 py-1 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-md"
              >
                <span className="flex-1 min-w-0 truncate text-xs font-medium text-[var(--color-text-primary)]">
                  {model}
                </span>
                <select
                  value={modelTypes[model] ?? typeDefaults[model] ?? ''}
                  onChange={(e) => onChangeModelType(model, e.target.value)}
                  aria-label={t('providerEdit.modelTypeOf', { name: model })}
                  className="text-xs bg-[var(--color-surface)] border border-[var(--color-border)] rounded px-1.5 py-0.5 text-[var(--color-text-secondary)] cursor-pointer shrink-0"
                >
                  <option value="">—</option>
                  {CATEGORY_ORDER.map((cat) => (
                    <option key={cat} value={cat}>
                      {t('providerEdit.category.' + cat)}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => onRemoveModel(model)}
                  className="p-0 bg-transparent border-none text-[var(--color-text-muted)] cursor-pointer hover:text-[var(--color-danger)] transition-colors shrink-0"
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex-1 flex items-center p-2 bg-[var(--color-surface-elevated)] border border-[var(--color-border)] rounded-md text-[var(--color-text-muted)] text-sm min-h-[36px]">
            <span>
              {apiKey
                ? t('providerEdit.noModelsWithKey')
                : t('providerEdit.enterApiKeyToFetch')}
            </span>
          </div>
        )}
        <button
          type="button"
          onClick={onFetchModels}
          disabled={!apiKey.trim() || fetching}
          title={t('providerEdit.fetchFromApi')}
          className="inline-flex items-center justify-center w-[36px] h-[36px] rounded-md cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
        >
          {fetching ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <RefreshCw size={14} />
          )}
        </button>
      </div>
    </div>
  );
}
