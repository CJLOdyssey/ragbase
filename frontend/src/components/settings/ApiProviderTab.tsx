import { useMemo, useState } from 'react';
import type * as React from 'react';
import LoadingSkeleton from '@/components/shared/LoadingSkeleton';
import { Button, ConfigProvider, Space, Switch, Table, Tooltip } from 'antd';
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
import CapabilityBadges from './CapabilityBadges';
import KeyTablePagination from './KeyTablePagination';
import {
  categoriesOf,
  CATEGORY_ORDER,
  type Category,
} from '../../utils/providerCategories';

const capsOf = (k: KeyItem): string[] =>
  (k as { capabilities?: string[] }).capabilities ?? [];

const FILTER_TAB_BASE =
  'px-2.5 py-1 rounded-md text-xs transition-colors cursor-pointer border-none';
const FILTER_TAB_ACTIVE =
  'bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)] text-[var(--color-accent)] font-medium';
const FILTER_TAB_IDLE =
  'bg-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]';

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
  const [filterCat, setFilterCat] = useState<'all' | Category>('all');
  const [page, setPage] = useState(1);
  const pageSize = 8;

  const visibleKeys = useMemo(() => {
    if (filterCat === 'all') return keys;
    return keys.filter((k) =>
      categoriesOf({ capabilities: capsOf(k) }).includes(filterCat),
    );
  }, [keys, filterCat]);

  const paginatedKeys = useMemo(() => {
    // 删除/停用后数据收缩：当前页可能越界（如第 2/2 页删空）——
    // 派生钳制到末页，避免空表 + 越界页码死区。
    const totalPages = Math.max(1, Math.ceil(visibleKeys.length / pageSize));
    const safePage = Math.min(page, totalPages);
    const start = (safePage - 1) * pageSize;
    return visibleKeys.slice(start, start + pageSize);
  }, [visibleKeys, page]);

  const handleFilterChange = (cat: 'all' | Category) => {
    setFilterCat(cat);
    setPage(1);
    setSelectedRowKeys([]);
  };

  const onPageChange = (p: number) => {
    setPage(p);
    setSelectedRowKeys([]);
  };

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
    return [
      {
        title: t('providerEdit.name'),
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
        title: t('providerEdit.secret'),
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
        title: t('providerEdit.purpose'),
        dataIndex: 'capabilities',
        key: 'capabilities',
        width: 150,
        render: (_: unknown, record: KeyItem) => (
          <CapabilityBadges capabilities={capsOf(record)} />
        ),
      },
      {
        title: t('providerEdit.lastUsed'),
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
        title: t('providerEdit.createdAt'),
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
        title: t('providerEdit.status'),
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
            <Tooltip title={t('providerEdit.edit')}>
              <Button
                type="text"
                size="small"
                icon={<Pencil size={13} />}
                onClick={() => onEdit(record)}
              />
            </Tooltip>
            <Tooltip title={t('providerEdit.test')}>
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
            <Tooltip title={t('confirm.delete')}>
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
        <h4>{t('providerEdit.keyManagement')}</h4>
        <div className="flex items-center gap-2">
          {selectedRowKeys.length > 0 && (
            <>
              <Button
                size="small"
                onClick={() => handleBatchActivate(true)}
                style={{ fontSize: 12, height: 28 }}
              >
                {t('providerEdit.enable')} ({selectedRowKeys.length})
              </Button>
              <Button
                size="small"
                onClick={() => handleBatchActivate(false)}
                style={{ fontSize: 12, height: 28 }}
              >
                {t('providerEdit.disable')} ({selectedRowKeys.length})
              </Button>
              <Button
                size="small"
                danger
                icon={<Trash2 size={12} />}
                onClick={handleBatchDelete}
                style={{ fontSize: 12, height: 28 }}
              >
                {t('confirm.delete')} ({selectedRowKeys.length})
              </Button>
            </>
          )}
          <Button
            type="primary"
            icon={<Plus size={14} />}
            onClick={onAdd}
            style={{ fontSize: 12, height: 28 }}
          >
            {t('providerEdit.addKey')}
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
      <div className="flex items-center gap-1 mb-2 pt-2 shrink-0">
        <button
          type="button"
          className={`${FILTER_TAB_BASE} ${filterCat === 'all' ? FILTER_TAB_ACTIVE : FILTER_TAB_IDLE}`}
          onClick={() => handleFilterChange('all')}
        >
          {t('providerEdit.filterAll')}
        </button>
        {CATEGORY_ORDER.map((cat) => (
          <button
            key={cat}
            type="button"
            className={`${FILTER_TAB_BASE} ${filterCat === cat ? FILTER_TAB_ACTIVE : FILTER_TAB_IDLE}`}
            onClick={() => handleFilterChange(cat)}
          >
            {t(`providerEdit.category.${cat}`)}
          </button>
        ))}
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="overflow-x-auto">
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
              dataSource={paginatedKeys}
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
      {visibleKeys.length > 0 && (
        <KeyTablePagination
          total={visibleKeys.length}
          current={Math.min(page, Math.max(1, Math.ceil(visibleKeys.length / pageSize)))}
          pageSize={pageSize}
          onChange={onPageChange}
        />
      )}
    </div>
  );
}
