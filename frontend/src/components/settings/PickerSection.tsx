import Modal from '@/components/shared/Modal';
import { Inbox } from 'lucide-react';
import type { PickerItem } from './tabs/usePickerState';

interface Props {
  tab: string | null;
  items: Record<string, PickerItem[]>;
  onSelect: (tab: string, item: PickerItem) => void;
  onClose: () => void;
}

const TITLE_MAP: Record<string, string> = {
  system: '系统提示词',
  output: '输出约束',
  tools: '工具',
  mcp: 'MCP',
  skills: 'Skills',
};

// ResourcePickerModal 轻量替代 —— 简单列表 + 点击加入
export default function PickerSection({
  tab,
  items,
  onSelect,
  onClose,
}: Props) {
  if (!tab) return null;

  const currentItems = items[tab] || [];

  return (
    <Modal
      title={`从工作台添加 - ${TITLE_MAP[tab] || tab}`}
      onClose={onClose}
      width={480}
      bodyClassName="p-4"
    >
      <div className="flex flex-col gap-2 max-h-[60vh] overflow-y-auto">
        {currentItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-[var(--color-text-muted)] text-center gap-3">
            <Inbox size={28} className="opacity-30" />
            <p className="text-sm">暂无项目</p>
          </div>
        ) : (
          currentItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className="flex flex-col gap-0.5 items-start px-3 py-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-lg text-left cursor-pointer transition-colors duration-150 hover:bg-[var(--color-surface-hover)]"
              onClick={() => onSelect(tab, item)}
            >
              <span className="text-sm font-medium text-[var(--color-text-primary)]">
                {item.name}
                {item.is_builtin === true && (
                  <span className="ml-1.5 inline-block py-0.5 px-1.5 rounded text-[10px] font-medium bg-[var(--color-accent)]/10 text-[var(--color-accent)] align-middle">
                    内置
                  </span>
                )}
              </span>
              {item.description && (
                <span className="text-xs text-[var(--color-text-muted)] line-clamp-2">
                  {item.description}
                </span>
              )}
            </button>
          ))
        )}
      </div>
    </Modal>
  );
}
