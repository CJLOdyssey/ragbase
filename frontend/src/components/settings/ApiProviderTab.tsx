import { useMemo, useState } from 'react';
import type * as React from 'react';
import LoadingSkeleton from '@/components/shared/LoadingSkeleton';
import {
  Button,
  ConfigProvider,
  Space,
  Switch,
  Table,
  Tag,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  AlertCircle,
  Key,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { KeyItem } from '../../api/client';

const USAGE_COLORS: Record<string, string> = {
  vector: 'var(--color-accent)',
  general: 'var(--color-success)',
  tool: 'var(--color-warning)',
};

interface Props {
  keys: KeyItem[];
  loading: boolean;
  error: string | null;
  testingId: string | null;
  onAdd: () => void;
  onEdit: (key: KeyItem) => void;
  onToggleActive: (id: string, active: boolean) => void;
  onTest: (key: KeyItem) => void;
  onDelete: (id: string) => void;
  onDismissError: () => void;
  onBatchDelete?: (ids: string[]) => void;
  onBatchToggleActive?: (ids: string[], active: boolean) => void;
}

export default function ApiProviderTab({
  keys,
  loading,
  error,
  testingId,
  onAdd,
  onEdit,
  onToggleActive,
  onTest,
  onDelete,
  onDismissError,
  onBatchDelete,
  onBatchToggleActive,
}: Props) {
  const { t } = useTranslation();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const handleBatchDelete = () => {
    if (onBatchDelete) onBatchDelete(selectedRowKeys as string[]);
    else selectedRowKeys.forEach((id) => onDelete(id as string));
    setSelectedRowKeys([]);
  };

  const handleBatchActivate = (active: boolean) => {
    if (onBatchToggleActive)
      onBatchToggleActive(selectedRowKeys as string[], active);
    else selectedRowKeys.forEach((id) => onToggleActive(id as string, active));
    setSelectedRowKeys([]);
  };

  const columns: ColumnsType<KeyItem> = useMemo(() => {
    const usageLabel = (type: string) => {
      if (type === 'tool') return t('api.type_tool');
      if (type === 'general') return t('api.type_general');
      if (type === 'vector') return t('api.type_vector');
      if (type === 'image') return t('api.type_image');
      if (type === 'audio') return t('api.type_audio');
      return t('api.type_chat');
    };
    return [
      {
        title: '名称',
        dataIndex: 'label',
        key: 'label',
        width: 90,
        render: (label: string, record: KeyItem) => (
          <span
            style={{
              fontWeight: 500,
              color: 'var(--color-text-primary)',
              maxWidth: 70,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              display: 'inline-block',
            }}
          >
            {label || record.provider}
          </span>
        ),
      },
      {
        title: '密钥',
        dataIndex: 'key_masked',
        key: 'key_masked',
        width: 110,
        render: (val: string) => (
          <code
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              color: 'var(--color-text-muted)',
            }}
          >
            {val}
          </code>
        ),
      },
      {
        title: '用途',
        dataIndex: 'usage_type',
        key: 'usage_type',
        width: 64,
        render: (type: string) => (
          <Tag
            color={USAGE_COLORS[type] ? undefined : 'default'}
            style={{
              fontSize: 11,
              lineHeight: '20px',
              padding: '0 8px',
              ...(USAGE_COLORS[type]
                ? {
                    background: `color-mix(in srgb, ${USAGE_COLORS[type]} 12%, transparent)`,
                    color: USAGE_COLORS[type],
                    borderColor: `color-mix(in srgb, ${USAGE_COLORS[type]} 25%, transparent)`,
                  }
                : {}),
            }}
          >
            {usageLabel(type)}
          </Tag>
        ),
      },
      {
        title: '上次使用',
        dataIndex: 'last_used_at',
        key: 'last_used_at',
        width: 80,
        render: (val: string | null) => (
          <span
            style={{
              fontSize: 12,
              color: 'var(--color-text-muted)',
              whiteSpace: 'nowrap',
            }}
          >
            {val ? new Date(val).toLocaleDateString() : ''}
          </span>
        ),
      },
      {
        title: '创建日期',
        dataIndex: 'created_at',
        key: 'created_at',
        width: 80,
        render: (val: string | null) => (
          <span
            style={{
              fontSize: 12,
              color: 'var(--color-text-muted)',
              whiteSpace: 'nowrap',
            }}
          >
            {val ? new Date(val).toLocaleDateString() : ''}
          </span>
        ),
      },
      {
        title: '状态',
        key: 'status',
        width: 56,
        align: 'center',
        render: (_: unknown, record: KeyItem) => (
          <Switch
            checked={record.is_active}
            size="small"
            onChange={(v) => onToggleActive(record.id, v)}
          />
        ),
      },
      {
        title: '',
        key: 'actions',
        width: 88,
        align: 'right',
        render: (_: unknown, record: KeyItem) => (
          <Space size={2}>
            <Tooltip title="编辑">
              <Button
                type="text"
                size="small"
                icon={<Pencil size={13} />}
                onClick={() => onEdit(record)}
              />
            </Tooltip>
            <Tooltip title="测试">
              <Button
                type="text"
                size="small"
                icon={
                  testingId === record.id ? (
                    <Loader2 size={13} className="animate-spin" />
                  ) : (
                    <RefreshCw size={13} />
                  )
                }
                onClick={() => onTest(record)}
                disabled={testingId === record.id}
              />
            </Tooltip>
            <Tooltip title="删除">
              <Button
                type="text"
                size="small"
                danger
                icon={<Trash2 size={13} />}
                onClick={() => onDelete(record.id)}
              />
            </Tooltip>
          </Space>
        ),
      },
    ];
  }, [testingId, onEdit, onTest, onDelete, onToggleActive, t]);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-4 shrink-0">
        <h4>密钥管理</h4>
        <div className="flex items-center gap-2">
          {selectedRowKeys.length > 0 && (
            <>
              <Button
                size="small"
                onClick={() => handleBatchActivate(true)}
                style={{ fontSize: 12, height: 28 }}
              >
                启用 ({selectedRowKeys.length})
              </Button>
              <Button
                size="small"
                onClick={() => handleBatchActivate(false)}
                style={{ fontSize: 12, height: 28 }}
              >
                禁用 ({selectedRowKeys.length})
              </Button>
              <Button
                size="small"
                danger
                icon={<Trash2 size={12} />}
                onClick={handleBatchDelete}
                style={{ fontSize: 12, height: 28 }}
              >
                删除 ({selectedRowKeys.length})
              </Button>
            </>
          )}
          <Button
            type="primary"
            icon={<Plus size={14} />}
            onClick={onAdd}
            style={{ fontSize: 12, height: 28 }}
          >
            添加 Key
          </Button>
        </div>
      </div>
      {error && (
        <div className="bg-[color-mix(in_srgb,var(--color-danger)_10%,transparent)] border border-[color-mix(in_srgb,var(--color-danger)_25%,transparent)] rounded-lg py-2.5 px-3.5 mb-4 flex items-center gap-2.5">
          <AlertCircle
            size={15}
            className="text-[var(--color-danger)] shrink-0"
          />
          <span className="text-[var(--color-danger)] text-sm flex-1">
            {error}
          </span>
          <button
            className="bg-transparent border-none text-[var(--color-text-muted)] cursor-pointer p-1 rounded hover:bg-[var(--color-surface-hover)] transition-colors"
            onClick={onDismissError}
          >
            ✕
          </button>
        </div>
      )}
      <div className="border-t border-[var(--color-border)] shrink-0" />
      <div className="flex-1 min-h-0 overflow-y-auto">
        {loading && keys.length === 0 ? (
          <LoadingSkeleton type="table" rows={4} />
        ) : (
          <ConfigProvider
            theme={{
              token: {
                colorBgContainer: 'var(--color-surface-raised)',
                colorBorderSecondary: 'transparent',
                colorText: 'var(--color-text-primary)',
                colorTextSecondary: 'var(--color-text-secondary)',
              },
              components: {
                Table: {
                  headerBg: 'var(--color-surface-raised)',
                  headerColor: 'var(--color-text-muted)',
                  rowHoverBg: 'var(--color-surface-hover)',
                  borderColor: 'transparent',
                },
              },
            }}
          >
            <Table<KeyItem>
              className="api-key-table"
              rowKey="id"
              columns={columns}
              dataSource={keys}
              pagination={false}
              size="small"
              rowSelection={{
                selectedRowKeys,
                onChange: (selected) => setSelectedRowKeys(selected),
                columnWidth: 36,
              }}
              locale={{
                emptyText: (
                  <div className="flex flex-col items-center py-10 text-[var(--color-text-muted)] text-center gap-3">
                    <Key size={28} className="opacity-30" />
                    <p className="text-sm">
                      {t('api.noKeys')}
                      <br />
                      {t('api.addKeyHint')}
                    </p>
                  </div>
                ),
              }}
            />
          </ConfigProvider>
        )}
      </div>
    </div>
  );
}
