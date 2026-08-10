import { useEffect, useState } from 'react';
import Modal from '@/components/shared/Modal';
import { AlertCircle, Loader2, Save, Tag, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { fetchModelsFromProvider } from '../../api/client/keys';
import { listModels } from '../../api/client/models';
import { listProviders, type ProvidersMap } from '../../api/client/providers';
import CredentialsSection from './CredentialsSection';
import ModelSection from './ModelSection';
import ProviderSelector from './ProviderSelector';
import { categoriesOf } from '../../utils/providerCategories';

export interface ApiProviderForm {
  id: string;
  provider: string;
  capabilities: string[];
  name: string;
  baseUrl: string;
  apiKey: string;
  models: string[];
  model_types?: Record<string, string> | null;
  isActive: boolean;
  status?: 'connected' | 'error' | 'untested';
}

const FALLBACK_PROVIDERS: ProvidersMap = {
  openai: {
    name: 'OpenAI',
    base_url: 'https://api.openai.com/v1',
    capabilities: ['chat', 'vector'],
    docs_url: null,
  },
  deepseek: {
    name: 'DeepSeek',
    base_url: 'https://api.deepseek.com',
    capabilities: ['chat'],
    docs_url: null,
  },
  anthropic: {
    name: 'Anthropic',
    base_url: 'https://api.anthropic.com',
    capabilities: ['chat'],
    docs_url: null,
  },
  dashscope: {
    name: 'DashScope',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    capabilities: ['chat', 'vector'],
    docs_url: null,
  },
  custom: {
    name: '自定义',
    base_url: '',
    capabilities: ['chat', 'vector'],
    docs_url: null,
  },
};

interface Props {
  provider: ApiProviderForm;
  onSave: (provider: ApiProviderForm) => void;
  onClose: () => void;
  saving?: boolean;
  error?: string | null;
  onCloseError?: () => void;
  /** 新建模式必须填写 API Key；编辑模式（明文不暴露）允许留空 */
  requireApiKey?: boolean;
}

function shouldShowModels(caps: string[]): boolean {
  if (caps.includes('tool')) return false;
  return caps.includes('chat') || caps.includes('image');
}

function fetchErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : '拉取模型失败';
}

function modalTitle(isEdit: boolean, t: (k: string) => string): string {
  return isEdit ? t('providerEdit.edit') : t('providerEdit.add');
}

function saveButtonLabel(saving: boolean, t: (k: string) => string): string {
  return saving ? '...' : t('providerEdit.save');
}

function FormErrorBanner({
  error,
  onCloseError,
}: {
  error: string;
  onCloseError?: () => void;
}) {
  return (
    <div className="bg-[color-mix(in_srgb,var(--color-danger)_10%,transparent)] border border-[color-mix(in_srgb,var(--color-danger)_25%,transparent)] rounded-lg py-2.5 px-3.5 flex items-start gap-2.5">
      <AlertCircle
        size={15}
        className="text-[var(--color-danger)] shrink-0 mt-0.5"
      />
      <span className="text-[var(--color-danger)] text-sm flex-1">{error}</span>
      {onCloseError && (
        <button
          type="button"
          onClick={onCloseError}
          className="bg-transparent border-none text-[var(--color-text-muted)] cursor-pointer p-0.5 rounded hover:bg-[var(--color-surface-hover)] transition-colors shrink-0"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}

export default function ProviderEditModal({
  provider,
  onSave,
  onClose,
  saving = false,
  error,
  onCloseError,
  requireApiKey = false,
}: Props) {
  const { t } = useTranslation();

  const [providers, setProviders] = useState<ProvidersMap>(FALLBACK_PROVIDERS);
  const [loadingProviders, setLoadingProviders] = useState(true);
  const [providerType, setProviderType] = useState(
    provider.provider || 'custom',
  );
  const [name, setName] = useState(provider.name);
  const [baseUrl, setBaseUrl] = useState(provider.baseUrl);
  const [apiKey, setApiKey] = useState(provider.apiKey);
  const [models, setModels] = useState<string[]>(provider.models);
  const [modelTypes, setModelTypes] = useState<Record<string, string>>(
    provider.model_types ?? {},
  );
  const [showKey, setShowKey] = useState(false);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [typeDefaults, setTypeDefaults] = useState<Record<string, string>>({});

  useEffect(() => {
    listProviders()
      .then(setProviders)
      .catch(() => {})
      .finally(() => setLoadingProviders(false));
  }, []);

  useEffect(() => {
    listModels()
      .then((infos) =>
        setTypeDefaults(Object.fromEntries(infos.map((i) => [i.id, i.type]))),
      )
      .catch(() => {});
  }, []);

  const info = providers[providerType];
  const caps = info?.capabilities ?? [];
  const isToolProvider = caps.includes('tool');
  const showModels = shouldShowModels(caps);

  const canSave =
    !saving && !!name.trim() && (!requireApiKey || !!apiKey.trim());

  const handleSave = () => {
    const preserveStored =
      Boolean(provider.id) && providerType === provider.provider;
    const capabilities = preserveStored
      ? (provider.capabilities ?? categoriesOf(info ?? {}))
      : categoriesOf(info ?? {});
    onSave({
      ...provider,
      provider: providerType,
      capabilities,
      name,
      baseUrl,
      apiKey,
      models,
      model_types: modelTypes,
    });
  };

  const handleFetchModels = async () => {
    if (!apiKey.trim()) return;
    setFetchingModels(true);
    setFetchError(null);
    try {
      const result = await fetchModelsFromProvider({
        api_key: apiKey,
        base_url: baseUrl,
        provider: providerType,
      });
      if (!result.success) {
        setFetchError(result.message || '拉取模型失败');
        return;
      }
      if (result.models.length > 0) {
        setModels((prev) => {
          const merged = new Set([...prev, ...result.models]);
          return Array.from(merged);
        });
      }
      setModelTypes(result.types ?? {});
    } catch (err) {
      setFetchError(fetchErrorMessage(err));
    } finally {
      setFetchingModels(false);
    }
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-3">
          <div className="w-[38px] h-[38px] rounded-[10px] bg-[color-mix(in_srgb,var(--color-surface),var(--color-text-primary)_8%)] flex items-center justify-center text-[var(--color-accent)] shrink-0">
            {loadingProviders ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Tag size={18} />
            )}
          </div>
          <div>
            <h3 className="m-0">{modalTitle(!!provider.id, t)}</h3>
          </div>
        </div>
      }
      onClose={onClose}
      width={480}
      bodyClassName="px-6 py-5 space-y-5"
      footer={
        <>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
            onClick={onClose}
          >
            {t('confirm.cancel')}
          </button>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-all duration-150 bg-[var(--color-accent)] text-white hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:brightness-100"
            onClick={handleSave}
            disabled={!canSave}
          >
            {saving ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Save size={14} />
            )}
            {saveButtonLabel(saving, t)}
          </button>
        </>
      }
    >
      {error && <FormErrorBanner error={error} onCloseError={onCloseError} />}
      {fetchError && (
        <FormErrorBanner
          error={fetchError}
          onCloseError={() => setFetchError(null)}
        />
      )}
      <div>
        <ProviderSelector
          providers={providers}
          providerType={providerType}
          onChangeProvider={setProviderType}
        />
      </div>

      <div className="pt-1">
        <CredentialsSection
          name={name}
          baseUrl={baseUrl}
          apiKey={apiKey}
          showKey={showKey}
          hideBaseUrl={isToolProvider}
          onChangeName={setName}
          onChangeBaseUrl={setBaseUrl}
          onChangeApiKey={setApiKey}
          onToggleShowKey={() => setShowKey(!showKey)}
        />
      </div>

      {showModels && (
        <div className="pt-1">
          <ModelSection
            models={models}
            modelTypes={modelTypes}
            typeDefaults={typeDefaults}
            fetching={fetchingModels}
            apiKey={apiKey}
            onRemoveModel={(m) => {
              setModels((prev) => prev.filter((x) => x !== m));
              setModelTypes((prev) => {
                const next = { ...prev };
                delete next[m];
                return next;
              });
            }}
            onChangeModelType={(m, type) =>
              setModelTypes((prev) => {
                const next = { ...prev };
                if (type) {
                  next[m] = type;
                } else {
                  delete next[m];
                }
                return next;
              })
            }
            onFetchModels={handleFetchModels}
          />
        </div>
      )}
    </Modal>
  );
}
