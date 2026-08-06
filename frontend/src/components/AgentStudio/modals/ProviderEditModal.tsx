import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Tag, Loader2, Save, AlertCircle } from 'lucide-react';
import { fetchModelsFromProvider } from '../../../api/client/keys';
import { listProviders } from '../../../api/client/providers';
import type { ProvidersMap } from '../../../api/client/providers';
import ProviderSelector from './ProviderSelector';
import CredentialsSection from './CredentialsSection';
import ModelSection from './ModelSection';
import Modal from '@/components/shared/Modal';

export interface ApiProviderForm {
  id: string;
  provider: string;
  usage_type: string;
  name: string;
  baseUrl: string;
  apiKey: string;
  models: string[];
  isActive: boolean;
  status?: 'connected' | 'error' | 'untested';
}

const FALLBACK_PROVIDERS: ProvidersMap = {
  openai:    { name: 'OpenAI',       base_url: 'https://api.openai.com/v1',                          capabilities: ['chat', 'vector'], docs_url: null },
  deepseek:  { name: 'DeepSeek',     base_url: 'https://api.deepseek.com',                           capabilities: ['chat'],            docs_url: null },
  anthropic: { name: 'Anthropic',    base_url: 'https://api.anthropic.com',                          capabilities: ['chat'],            docs_url: null },
  dashscope: { name: 'DashScope',    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',  capabilities: ['chat', 'vector'], docs_url: null },
  custom:    { name: '自定义',       base_url: '',                                                    capabilities: ['chat', 'vector'], docs_url: null },
};

interface Props {
  provider: ApiProviderForm;
  onSave: (provider: ApiProviderForm) => void;
  onClose: () => void;
  saving?: boolean;
  error?: string | null;
  onCloseError?: () => void;
}

export default function ProviderEditModal({ provider, onSave, onClose, saving = false, error, onCloseError }: Props) {
  const { t } = useTranslation();

  const [providers, setProviders] = useState<ProvidersMap>(FALLBACK_PROVIDERS);
  const [loadingProviders, setLoadingProviders] = useState(true);
  const [providerType, setProviderType] = useState(provider.provider || 'custom');
  const [usageType, setUsageType] = useState<string>(provider.usage_type || 'chat');
  const [name, setName] = useState(provider.name);
  const [baseUrl, setBaseUrl] = useState(provider.baseUrl);
  const [apiKey, setApiKey] = useState(provider.apiKey);
  const [models, setModels] = useState<string[]>(provider.models);
  const [showKey, setShowKey] = useState(false);
  const [fetchingModels, setFetchingModels] = useState(false);

  useEffect(() => {
    listProviders()
      .then(setProviders)
      .catch(() => {})
      .finally(() => setLoadingProviders(false));
  }, []);

  const [prevProviderType, setPrevProviderType] = useState<string | null>(null);
  // Sync usageType/baseUrl to the selected provider's defaults when provider changes.
  // Render-phase state adjustment (React-sanctioned) instead of setState-in-effect.
  if (prevProviderType !== providerType) {
    setPrevProviderType(providerType);
    const info = providers[providerType];
    if (info) {
      const caps = info.capabilities ?? ['chat'];
      const isTool = caps.includes('tool');
      if (isTool) {
        setUsageType('tool');
      } else {
        const derived = caps.includes('chat') && caps.includes('vector') ? 'general' : caps[0];
        if (derived !== usageType) setUsageType(derived);
      }
      if (info.base_url && !isTool) {
        const knownDefaults = Object.values(providers).map((p) => p.base_url).filter(Boolean);
        if (!baseUrl || knownDefaults.includes(baseUrl)) {
          setBaseUrl(info.base_url);
        }
      }
    }
  }

  const info = providers[providerType];
  const caps = info?.capabilities ?? [];
  const isToolProvider = caps.includes('tool');
  const showModels = !isToolProvider && (usageType === 'chat' || usageType === 'general' || usageType === 'image' || usageType === 'audio');

  const handleSave = () => {
    onSave({
      ...provider, provider: providerType, usage_type: usageType,
      name, baseUrl, apiKey, models,
    });
  };

  const handleFetchModels = async () => {
    if (!apiKey.trim()) return;
    setFetchingModels(true);
    try {
      const result = await fetchModelsFromProvider({
        api_key: apiKey, base_url: baseUrl || undefined, provider: providerType,
      });
      if (result.success && result.models.length > 0) {
        setModels((prev) => {
          const merged = new Set([...prev, ...result.models]);
          return Array.from(merged);
        });
      }
    } catch { /* ignore */ }
    finally { setFetchingModels(false); }
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-3">
          <div className="w-[38px] h-[38px] rounded-[10px] bg-[color-mix(in_srgb,var(--color-surface),var(--color-text-primary)_8%)] flex items-center justify-center text-[var(--color-accent)] shrink-0">
            {loadingProviders ? <Loader2 size={16} className="animate-spin" /> : <Tag size={18} />}
          </div>
          <div>
            <h3 className="m-0">{provider.id ? t('providerEdit.edit') : t('providerEdit.add')}</h3>
          </div>
        </div>
      }
      onClose={onClose}
      width={480}
      bodyClassName="px-6 py-5 space-y-5"
      footer={
        <>
          <button type="button" className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]" onClick={onClose}>{t('confirm.cancel')}</button>
          <button type="button" className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-all duration-150 bg-[var(--color-accent)] text-white hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:brightness-100" onClick={handleSave} disabled={!name.trim() || !apiKey.trim() || saving}>
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            {saving ? '...' : t('providerEdit.save')}
          </button>
        </>
      }
    >
      {error && (
            <div className="bg-[color-mix(in_srgb,var(--color-danger)_10%,transparent)] border border-[color-mix(in_srgb,var(--color-danger)_25%,transparent)] rounded-lg py-2.5 px-3.5 flex items-start gap-2.5">
              <AlertCircle size={15} className="text-[var(--color-danger)] shrink-0 mt-0.5" />
              <span className="text-[var(--color-danger)] text-sm flex-1">{error}</span>
              {onCloseError && (
                <button type="button" onClick={onCloseError}
                  className="bg-transparent border-none text-[var(--color-text-muted)] cursor-pointer p-0.5 rounded hover:bg-[var(--color-surface-hover)] transition-colors shrink-0">
                  <X size={14} />
                </button>
              )}
            </div>
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
              name={name} baseUrl={baseUrl} apiKey={apiKey}
              showKey={showKey} hideBaseUrl={isToolProvider}
              onChangeName={setName} onChangeBaseUrl={setBaseUrl}
              onChangeApiKey={setApiKey}
              onToggleShowKey={() => setShowKey(!showKey)}
            />
          </div>

          {showModels && (
            <div className="pt-1">
              <ModelSection
                models={models} fetching={fetchingModels} apiKey={apiKey}
                onRemoveModel={(m) => setModels((prev) => prev.filter((x) => x !== m))}
                onFetchModels={handleFetchModels}
              />
            </div>
          )}
    </Modal>
  );
}
