import { useState } from 'react';
import { Modal as AntdModal } from 'antd';
import { Globe, Key, Server } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import ApiProviderTab from './ApiProviderTab';
import ApiUsageTab from './ApiUsageTab';
import ConfirmModal from './ConfirmModal';
import ModelSelector from './ModelSelector';
import ProviderEditModal from './ProviderEditModal';
import { useApiKeys } from './useApiKeys';

interface Props {
  onClose: () => void;
}

type ApiTab = 'keys' | 'models' | 'usage';

export default function ApiManagementModal({ onClose }: Props) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<ApiTab>('keys');
  const {
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
  } = useApiKeys();

  const TABS = ['keys', 'models', 'usage'] as const;
  const TAB_ICONS: Record<ApiTab, typeof Server> = {
    keys: Server,
    models: Globe,
    usage: Key,
  };

  return (
    <AntdModal
      title="API"
      open={true}
      onCancel={onClose}
      centered
      width={970}
      footer={null}
      className="api-modal"
      styles={{ body: { padding: 12 } }}
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
    </AntdModal>
  );
}
