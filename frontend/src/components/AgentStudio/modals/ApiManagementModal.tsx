import { useState, useEffect } from 'react';
import { Key, Server, Globe } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useQueryClient } from '@tanstack/react-query';
import Modal from '../../shared/Modal';
import ProviderEditModal from './ProviderEditModal';
import ApiProviderTab from './ApiProviderTab';
import ApiUsageTab from './ApiUsageTab';
import ModelSelector from './ModelSelector';
import ConfirmModal from './ConfirmModal';
import * as api from '../../../api/client';
import type { KeyItem } from '../../../api/client';
import Logger from '../../../utils/logger';

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
      return localStorage.getItem('agentstudio-selected-model') || '';
    } catch {
      return '';
    }
  });
  const [usage, setUsage] = useState({ today_requests: 0, today_tokens: 0, month_requests: 0, month_tokens: 0 });

  const [error, setError] = useState<string | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

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

  const handleSaveKey = async (keyData: {
    provider: string;
    usage_type?: string;
    label: string;
    apiKey: string;
    baseUrl: string;
    models: string[];
  }) => {
    setModalError(null);
    const maskedNew = maskKey(keyData.apiKey);
    const dup = keys.find((k) => k.key_masked === maskedNew);
    if (dup) {
      setModalError(`密钥已存在于「${dup.label || dup.provider}」中，请勿重复添加`);
      return;
    }
    setSaving(true);
    try {
      await api.createKey({
        provider: keyData.provider,
        usage_type: keyData.usage_type,
        label: keyData.label,
        api_key: keyData.apiKey,
        base_url: keyData.baseUrl || undefined,
        models: keyData.models,
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
      usage_type?: string;
      label?: string;
      apiKey?: string;
      baseUrl?: string;
      models?: string[];
      isActive?: boolean;
      isDefault?: boolean;
    },
  ) => {
    setError(null);
    try {
      await api.updateKey(id, {
        label: updates.label,
        api_key: updates.apiKey,
        base_url: updates.baseUrl,
        models: updates.models,
        is_active: updates.isActive,
        is_default: updates.isDefault,
      });
      await loadKeys();
      void queryClient.invalidateQueries({ queryKey: ['keys'] });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t('api.updateFailed');
      setError(msg);
      Logger.error('Failed to update API key', err);
    }
  };

  const handleDeleteKey = (id: string) => {
    setConfirmDeleteId(id);
  };

  const confirmDeleteAction = async () => {
    if (!confirmDeleteId) return;
    setError(null);
    try {
      await api.deleteKey(confirmDeleteId);
      await loadKeys();
      void queryClient.invalidateQueries({ queryKey: ['keys'] });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t('api.deleteFailed');
      setError(msg);
      Logger.error('Failed to delete API key', err);
    }
    setConfirmDeleteId(null);
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

  const allModels = keys.filter((k) => k.is_active).flatMap((k) => k.models.map((m) => ({ model: m, keyId: k.id })));

  const showAddForm = () => {
    setEditingKey({
      id: '',
      provider: 'custom',
            usage_type: 'chat',
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
    localStorage.setItem('agentstudio-selected-model', model);
    window.dispatchEvent(new Event('agentstudio-model-changed'));
  };

const TABS = ['keys', 'models', 'usage'] as const;
const TAB_ICONS: Record<ApiTab, typeof Server> = { keys: Server, models: Globe, usage: Key };

  return (
    <Modal title="API 管理" onClose={onClose} className="api-modal" hideHeaderBorder bodyClassName="p-3">
      <div className="flex h-full min-h-0 overflow-hidden">
        <div className="w-[160px] px-4 py-5 flex flex-col gap-1 overflow-hidden min-h-0">
          {TABS.map((tab) => {
            const Icon = TAB_ICONS[tab];
            const label = tab === 'keys' ? t('api.tab_api') : tab === 'models' ? t('api.tab_model') : t('api.tab_usage');
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
              onToggleActive={(id, active) => handleUpdateKey(id, { isActive: active })}
              onTest={handleTestConnection}
              onDelete={handleDeleteKey}
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
          {activeTab === 'usage' && (
            <ApiUsageTab usage={usage} />
          )}
        </div>
      </div>
      {editingKey && (
        <ProviderEditModal
          provider={{
            id: editingKey.id,
            provider: editingKey.provider,
            usage_type: editingKey.usage_type || 'chat',
            name: editingKey.label || editingKey.provider,
            baseUrl: editingKey.base_url || '',
            apiKey: '',
            models: editingKey.models,
            isActive: editingKey.is_active,
            status: 'untested' as const,
          }}
          saving={saving}
          error={modalError}
          onCloseError={() => setModalError(null)}
          onSave={async (form) => {
            const label = form.name.trim() || (() => {
              const count = keys.filter((k) => k.provider === form.provider).length + 1;
              return `${form.provider}-${count}`;
            })();
            if (editingKey.id) {
              await handleUpdateKey(editingKey.id, {
                label,
                usage_type: form.usage_type,
                apiKey: form.apiKey || undefined,
                baseUrl: form.baseUrl || undefined,
                models: form.models,
              });
            } else {
              await handleSaveKey({
                provider: form.provider,
                usage_type: form.usage_type,
                label,
                apiKey: form.apiKey,
                baseUrl: form.baseUrl,
                models: form.models,
              });
            }
          }}
          onClose={() => {
            if (!saving) { setEditingKey(null); setModalError(null); }
          }}
        />
      )}
      {confirmDeleteId && (
        <ConfirmModal
          title={t('confirm.title', '确认删除')}
          message={t('api.deleteKeyConfirm', '确定要删除此 API Key 吗？此操作不可撤销。')}
          onConfirm={confirmDeleteAction}
          onCancel={() => setConfirmDeleteId(null)}
          danger
        />
      )}
    </Modal>
  );
}
