import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import * as api from '../../api/client';
import type { KeyItem } from '../../api/client';
import Logger from '../../utils/logger';

function maskKey(raw: string): string {
  if (raw.length <= 8) return raw.slice(0, 2) + '***';
  return raw.slice(0, 3) + '...' + raw.slice(-4);
}

// API 管理 Modal 的数据层：keys/usage/模型类型加载、CRUD、测试连接、
// 模型选择（localStorage 持久化）。UI 层只消费返回的状态与处理器。
export function useApiKeys() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
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
      // Background model fetch may still be in flight — refresh once shortly
      // so the model list populates without a manual reload.
      window.setTimeout(() => {
        void loadKeys();
        void queryClient.invalidateQueries({ queryKey: ['keys'] });
      }, 2000);
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

  const allModels = keys
    .filter((k) => k.is_active)
    .flatMap((k) =>
      k.models.map((m) => ({
        model: m,
        keyId: k.id,
        type: modelTypeMap.get(m) ?? 'llm',
      })),
    );

  return {
    keys,
    loading,
    error,
    modalError,
    saving,
    editingKey,
    testingId,
    selectedModel,
    usage,
    allModels,
    confirmDeleteIds,
    setEditingKey,
    setModalError,
    setError,
    setConfirmDeleteIds,
    showAddForm,
    handleUpdateKey,
    handleSaveKey,
    handleDeleteKey,
    handleBatchDelete,
    handleTestConnection,
    confirmDeleteAction,
    handleModelSelect,
  };
}
