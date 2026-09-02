import { useTranslation } from 'react-i18next';

interface Props {
  page: number;
  totalPages: number;
  total: number;
  onPageChange: (next: number) => void;
}

/**
 * 日志列表分页脚 —— 总条数 + 翻页交互（数据获取与布局归父组件）。
 * 单页时隐藏翻页按钮，但总条数恒显（筛选后共 0 条也是有效反馈）。
 */
export default function LogsPagination({
  page,
  totalPages,
  total,
  onPageChange,
}: Props) {
  const { t } = useTranslation();
  if (totalPages <= 1) {
    return (
      <div className="text-center text-sm text-[var(--color-text-muted)] mt-6">
        {t('retrievalLogs.totalCount', { total })}
      </div>
    );
  }

  const btn =
    'px-3 py-1.5 rounded-md text-sm bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)] border-none cursor-pointer disabled:opacity-40';

  return (
    <div className="flex items-center justify-center gap-3 mt-6">
      <span className="text-sm text-[var(--color-text-muted)]">
        {t('retrievalLogs.totalCount', { total })}
      </span>
      <button
        className={btn}
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        {t('common.prev')}
      </button>
      <span className="text-sm text-[var(--color-text-muted)]">
        {page} / {totalPages}
      </span>
      <button
        className={btn}
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
      >
        {t('common.next')}
      </button>
    </div>
  );
}
