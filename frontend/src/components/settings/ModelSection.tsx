import { Loader2, RefreshCw, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface Props {
  models: string[];
  fetching: boolean;
  apiKey: string;
  onRemoveModel: (model: string) => void;
  onFetchModels: () => void;
}

export default function ModelSection({
  models,
  fetching,
  apiKey,
  onRemoveModel,
  onFetchModels,
}: Props) {
  const { t } = useTranslation();

  return (
    <div>
      <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">
        {t('providerEdit.supportedModels')}
      </label>
      <div className="flex items-start gap-2">
        {models.length > 0 ? (
          <div className="flex-1 flex flex-wrap gap-1.5 p-2 bg-[var(--color-surface-elevated)] border border-[var(--color-border)] rounded-md min-h-[36px]">
            {models.map((model) => (
              <span
                key={model}
                className="inline-flex items-center gap-1 px-2 py-0.5 bg-[var(--color-accent)] text-white rounded text-xs font-medium"
              >
                {model}
                <button
                  type="button"
                  onClick={() => onRemoveModel(model)}
                  className="p-0 bg-transparent border-none text-white/60 cursor-pointer hover:text-white transition-colors"
                >
                  <X size={12} />
                </button>
              </span>
            ))}
          </div>
        ) : (
          <div className="flex-1 flex items-center p-2 bg-[var(--color-surface-elevated)] border border-[var(--color-border)] rounded-md text-[var(--color-text-muted)] text-sm min-h-[36px]">
            <span>
              {apiKey
                ? t('providerEdit.noModelsWithKey')
                : t('workstation.enterApiKeyToFetch')}
            </span>
          </div>
        )}
        <button
          type="button"
          onClick={onFetchModels}
          disabled={!apiKey.trim() || fetching}
          title={t('workstation.fetchFromApi')}
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
