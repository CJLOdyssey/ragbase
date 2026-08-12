import { useEffect, useState } from 'react';
import Modal from '@/components/shared/Modal';
import { useQueryClient } from '@tanstack/react-query';
import { Globe, Key, Server } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import * as api from '../../api/client';
import type { KeyItem } from '../../api/client';
import ApiProviderTab from './ApiProviderTab';
import ApiUsageTab from './ApiUsageTab';
import ConfirmModal from './ConfirmModal';
import ModelSelector from './ModelSelector';
import ProviderEditModal from './ProviderEditModal';
import Logger from '../../utils/logger';

function maskKey(raw: string): string {
  if (raw.length <= 8) return raw.slice(0, 2) + '***';
  return raw.slice(0, 3) + '...' + raw.slice(-4);
}

interface Props {
  onClose: () => void;
}

type ApiTab = 'keys' | 'models' | 'usage';

export default function ApiManagementModal({ onClose }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<ApiTab>('keys');
  const [keys, setKeys] = useState<KeyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingKey, setEditingKey] = useState<KeyItem | null>(null);

  const [testingId, setTestingId] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>(() => {
    try {
      return localStorage.getItem('ragbase-selected-model') || '';
    } catch {
      return '';
    }
  });
  const [usage, setUsage] = useState({
    today_requests: 0,
    today_tokens: 0,
    month_requests: 0,
    month_tokens: 0,
  });

  const [error, setError] = useState<string | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmDeleteIds, setConfirmDeleteIds] = useState<string[] | null>(
    null,
  );
  const [modelTypeMap, setModelTypeMap] = useState<Map<string, string>>(
    new Map(),
  );

  const loadKeys = async () => {
    try {
      setLoading(true);
      const serverKeys = await api.listKeys();
      setKeys(serverKeys);
    } catch (err) {
      Logger.warn('Failed to load API keys from server', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    api
      .listKeys()
      .then((serverKeys) => {
        if (!cancelled) setKeys(serverKeys);
      })
      .catch((err) => Logger.warn('Failed to load API keys from server', err))
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    api
      .getKeyUsage()
      .then((data) => {
        if (!cancelled) setUsage(data);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [keys]);

  // Model type map from /api/models — feeds the model tab grouping. Failure
  // falls back to the ModelSelector's own 'llm' default; never crashes the modal.
  useEffect(() => {
    let cancelled = false;
    api
      .listModels()
      .then((infos) => {
        if (!cancelled) {
          setModelTypeMap(new Map(infos.map((i) => [i.id, i.type])));
        }
      })
      .catch((err) =>
        Logger.warn('Failed to load model types from server', err),
      );
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSaveKey = async (keyData: {
    provider: string;
    capabilities?: string[];
    label: string;
    apiKey: string;
    baseUrl: string;
    models: string[];
    model_types?: Record<string, string>;
  }) => {
    setModalError(null);
    const maskedNew = maskKey(keyData.apiKey);
    const dup = keys.find((k) => k.key_masked === maskedNew);
    if (dup) {
      setModalError(
        t('providerEdit.keyExists', { name: dup.label || dup.provider }),
      );
      return;
    }
    setSaving(true);
    try {
      await api.createKey({
        provider: keyData.provider,
        capabilities: keyData.capabilities,
        label: keyData.label,
        api_key: keyData.apiKey,
        base_url: keyData.baseUrl || undefined,
        models: keyData.models,
        model_types: keyData.model_types,
        is_default: false,
      });
      await loadKeys();
      void queryClient.invalidateQueries({ queryKey: ['keys'] });
      setEditingKey(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t('api.saveFailed');
      setError(msg);
      Logger.error('Failed to save API key', err);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateKey = async (
    id: string,
    updates: {
      capabilities?: string[];
      label?: string;
      apiKey?: string;
      baseUrl?: string;
      models?: string[];
      model_types?: Record<string, string>;
      isActive?: boolean;
      isDefault?: boolean;
    },
  ): Promise<boolean> => {
    setError(null);
    try {
      await api.updateKey(id, {
        capabilities: updates.capabilities,
        label: updates.label,
        api_key: updates.apiKey,
        base_url: updates.baseUrl,
        models: updates.models,
        model_types: updates.model_types,
        is_active: updates.isActive,
        is_default: updates.isDefault,
      });
      await loadKeys();
      void queryClient.invalidateQueries({ queryKey: ['keys'] });
      return true;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t('api.updateFailed');
      setError(msg);
      Logger.error('Failed to update API key', err);
      return false;
    }
  };

  const handleDeleteKey = (id: string) => {
    setConfirmDeleteIds([id]);
  };

  const handleBatchDelete = (ids: string[]) => {
    setConfirmDeleteIds(ids);
  };

  const confirmDeleteAction = async () => {
    if (!confirmDeleteIds || confirmDeleteIds.length === 0) return;
    setError(null);
    try {
      await Promise.all(confirmDeleteIds.map((id) => api.deleteKey(id)));
      await loadKeys();
      void queryClient.invalidateQueries({ queryKey: ['keys'] });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t('api.deleteFailed');
      setError(msg);
      Logger.error('Failed to delete API key', err);
    }
    setConfirmDeleteIds(null);
  };

  const handleTestConnection = async (key: KeyItem) => {
    setTestingId(key.id);
    try {
      const result = await api.testKeyConnection(key.id);
      if (result.success) {
        alert(t('api.testSuccess'));
      } else {
        alert(t('api.testFail') + ': ' + result.message);
      }
    } catch {
      alert(t('api.testError'));
    }
    setTestingId(null);
  };

  const allModels = keys
    .filter((k) => k.is_active)
    .flatMap((k) =>
      k.models.map((m) => ({
        model: m,
        keyId: k.id,
        type: modelTypeMap.get(m) ?? 'llm',
      })),
    );

  const showAddForm = () => {
    setEditingKey({
      id: '',
      provider: 'openai',
      capabilities: [],
      label: '',
      key_masked: '',
      base_url: '',
      models: [],
      is_active: true,
      is_default: keys.length === 0,
      last_used_at: null,
      created_at: null,
    });
  };

  const handleModelSelect = (model: string) => {
    setSelectedModel(model);
    localStorage.setItem('ragbase-selected-model', model);
    window.dispatchEvent(new Event('ragbase-model-changed'));
  };

  const TABS = ['keys', 'models', 'usage'] as const;
  const TAB_ICONS: Record<ApiTab, typeof Server> = {
    keys: Server,
    models: Globe,
    usage: Key,
  };

  return (
    <Modal
      title="API"
      onClose={onClose}
      className="api-modal"
      hideHeaderBorder
      bodyClassName="p-3"
    >
      <div className="flex h-full min-h-0 overflow-hidden">
        <div className="w-[160px] px-4 py-5 flex flex-col gap-1 overflow-hidden min-h-0">
          {TABS.map((tab) => {
            const Icon = TAB_ICONS[tab];
            const label =
              tab === 'keys'
                ? t('api.tab_api')
                : tab === 'models'
                  ? t('api.tab_model')
                  : t('api.tab_usage');
            return (
              <button
                key={tab}
                className={`flex items-center gap-3 p-2 px-3 bg-transparent border-none rounded-md text-[var(--color-text-secondary)] text-sm cursor-pointer transition-[background,color] duration-150 text-left hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] ${activeTab === tab ? 'bg-[var(--color-surface-hover)] text-[var(--color-text-primary)]' : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                <Icon size={16} />
                <span>{label}</span>
              </button>
            );
          })}
        </div>
        <div className="flex-1 px-6 overflow-hidden min-h-0">
          {activeTab === 'keys' && (
            <ApiProviderTab
              keys={keys}
              loading={loading}
              error={error}
              testingId={testingId}
              onAdd={showAddForm}
              onEdit={setEditingKey}
              onToggleActive={(id, active) =>
                handleUpdateKey(id, { isActive: active })
              }
              onTest={handleTestConnection}
              onDelete={handleDeleteKey}
              onBatchDelete={handleBatchDelete}
              onDismissError={() => setError(null)}
            />
          )}
          {activeTab === 'models' && (
            <ModelSelector
              models={allModels}
              selectedModel={selectedModel}
              onSelect={handleModelSelect}
            />
          )}
          {activeTab === 'usage' && <ApiUsageTab usage={usage} />}
        </div>
      </div>
      {editingKey && (
        <ProviderEditModal
          provider={{
            id: editingKey.id,
            provider: editingKey.provider,
            capabilities: editingKey.capabilities,
            name: editingKey.id ? editingKey.label : '',
            baseUrl: editingKey.base_url || '',
            apiKey: '',
            models: editingKey.models,
            model_types: editingKey.model_types ?? undefined,
            isActive: editingKey.is_active,
            status: 'untested' as const,
          }}
          saving={saving}
          error={modalError}
          requireApiKey={!editingKey.id}
          onCloseError={() => setModalError(null)}
          onSave={async (form) => {
            const label =
              form.name.trim() ||
              (() => {
                const count =
                  keys.filter((k) => k.provider === form.provider).length + 1;
                return `${form.provider}-${count}`;
              })();
            if (editingKey.id) {
              const ok = await handleUpdateKey(editingKey.id, {
                label,
                capabilities: form.capabilities,
                apiKey: form.apiKey || undefined,
                baseUrl: form.baseUrl || undefined,
                models: form.models,
                model_types: form.model_types ?? undefined,
              });
              if (ok) {
                setEditingKey(null);
                setModalError(null);
              }
            } else {
              await handleSaveKey({
                provider: form.provider,
                capabilities: form.capabilities,
                label,
                apiKey: form.apiKey,
                baseUrl: form.baseUrl,
                models: form.models,
                model_types: form.model_types ?? undefined,
              });
            }
          }}
          onClose={() => {
            if (!saving) {
              setEditingKey(null);
              setModalError(null);
            }
          }}
        />
      )}
      {confirmDeleteIds && (
        <ConfirmModal
          title={t('confirm.title')}
          message={
            confirmDeleteIds.length > 1
              ? t('providerEdit.deleteKeysConfirm', {
                  count: confirmDeleteIds.length,
                })
              : t('providerEdit.deleteKeyConfirm')
          }
          onConfirm={confirmDeleteAction}
          onCancel={() => setConfirmDeleteIds(null)}
          danger
        />
      )}
    </Modal>
  );
}
