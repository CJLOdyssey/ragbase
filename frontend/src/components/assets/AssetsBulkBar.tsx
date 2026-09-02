import { useRef, useState, type CSSProperties } from 'react';
import { createPortal } from 'react-dom';
import { BookOpen, ChevronDown, Search, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { KnowledgeBase } from '../../api/client/knowledgeBases';

interface AssetsBulkBarProps {
  count: number;
  kbs: KnowledgeBase[];
  assigning: boolean;
  indexing: boolean;
  canIndex: boolean;
  onAssign: (kbId: string) => void;
  onIndex: () => void;
  onCancel: () => void;
}

/**
 * 批量操作条 — 表格正上方（AntD Table 批量操作模式）。
 * 动作按行业流水线顺序排列：分配知识库（归属）→ 建立索引（分块+向量化）。
 * 通过回调与页面解耦（DIP），自身不持有任何业务状态。
 */
export default function AssetsBulkBar({
  count,
  kbs,
  assigning,
  indexing,
  canIndex,
  onAssign,
  onIndex,
  onCancel,
}: AssetsBulkBarProps) {
  const { t } = useTranslation();
  const [kbOpen, setKbOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  // 下拉紧贴触发按钮正下方（右对齐），与行内菜单视觉语言一致。
  // 位置在点击时同步计算（非 effect）——避免首帧渲染在错误位置。
  const [menuPos, setMenuPos] = useState<CSSProperties>({});

  const openKbMenu = () => {
    const rect = triggerRef.current?.getBoundingClientRect();
    if (rect) {
      setMenuPos({
        top: rect.bottom + 6,
        right: Math.max(8, window.innerWidth - rect.right),
      });
    }
    setKbOpen(true);
  };
  // 关闭只靠全屏遮罩 onClick——不用 document mousedown 监听：
  // 菜单 portal 在 body，会被 outside-close 在 mousedown 阶段提前卸载，
  // 导致菜单项的 click 永远不触发（曾致批量分配无响应）。

  const busy = assigning || indexing;

  return (
    <div
      ref={rootRef}
      data-testid="assets-bulk-bar"
      className="relative flex items-center gap-3 rounded-[12px] border border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)] bg-[color-mix(in_srgb,var(--color-accent)_7%,transparent)] px-4 py-2.5"
    >
      <span className="text-sm font-medium text-[var(--color-text-primary)]">
        {t('assets.bulk.selected', { count })}
      </span>

      <div className="ml-auto flex items-center gap-2">
        {/* ① 归属：分配到知识库 */}
        <button
          type="button"
          ref={triggerRef}
          disabled={busy || kbs.length === 0}
          onClick={openKbMenu}
          aria-expanded={kbOpen}
          aria-haspopup="menu"
          data-testid="bulk-assign-trigger"
          className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border-none bg-[var(--color-accent)] px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <BookOpen size={12} />
          {kbs.length === 0
            ? t('assets.bulk.noKbs')
            : t('assets.bulk.assignTo')}
          <ChevronDown
            size={11}
            className={`transition-transform ${kbOpen ? 'rotate-180' : ''}`}
          />
        </button>

        {/* ② 索引：分块 + 向量化 */}
        <button
          type="button"
          disabled={busy || !canIndex}
          onClick={onIndex}
          title={canIndex ? undefined : t('assets.bulk.indexDisabledHint')}
          data-testid="bulk-index"
          className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Search size={12} />
          {indexing ? t('assets.bulk.indexing') : t('assets.bulk.index')}
        </button>

        <button
          type="button"
          disabled={busy}
          onClick={onCancel}
          aria-label={t('assets.bulk.cancel')}
          data-testid="bulk-cancel"
          className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-full border-none bg-transparent p-0 text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] disabled:cursor-not-allowed"
        >
          <X size={14} />
        </button>
      </div>

      {kbOpen &&
        kbs.length > 0 &&
        createPortal(
          <div
            style={{ position: 'fixed', inset: 0, zIndex: 999 }}
            onClick={() => setKbOpen(false)}
          >
            <div
              role="menu"
              aria-label={t('assets.bulk.assignTo')}
              style={menuPos}
              className="absolute min-w-[180px] max-h-[280px] overflow-y-auto rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-raised)] py-1 shadow-[0_12px_40px_rgba(0,0,0,0.3)]"
              onClick={(e) => e.stopPropagation()}
            >
              {kbs.map((kb) => (
                <button
                  key={kb.id}
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setKbOpen(false);
                    onAssign(kb.id);
                  }}
                  data-testid={`bulk-assign-kb-${kb.id}`}
                  className="flex w-full items-center gap-2 border-none bg-transparent px-3 py-2 text-left text-sm text-[var(--color-text-primary)] cursor-pointer hover:bg-[var(--color-surface-hover)]"
                >
                  <BookOpen
                    size={12}
                    className="shrink-0 text-[var(--color-text-muted)]"
                  />
                  {kb.name}
                </button>
              ))}
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
}
