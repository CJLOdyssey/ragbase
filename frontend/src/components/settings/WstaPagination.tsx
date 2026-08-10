import { Pagination, type PaginationProps } from 'antd';
import { useTranslation } from 'react-i18next';

interface WstaPaginationProps extends Omit<
  PaginationProps,
  'size' | 'showTotal'
> {
  total: number;
  current: number;
  pageSize: number;
  onChange: (page: number) => void;
}

export default function WstaPagination({
  total,
  current,
  pageSize,
  onChange,
  ...rest
}: WstaPaginationProps) {
  const { t } = useTranslation();
  if (total === 0) return null;
  return (
    <div
      className="flex items-center justify-between px-6 pt-3 gap-4"
      style={{ paddingBottom: 40 }}
    >
      <span className="text-[14px] text-[var(--color-text-muted)] tabular-nums whitespace-nowrap font-medium">
        {t('providerEdit.totalCount', { count: total })}
      </span>
      <Pagination
        current={current}
        pageSize={pageSize}
        total={total}
        onChange={onChange}
        showSizeChanger={false}
        showQuickJumper
        showLessItems
        {...rest}
      />
    </div>
  );
}
