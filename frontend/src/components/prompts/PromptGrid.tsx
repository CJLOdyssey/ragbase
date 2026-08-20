import type { PromptItem } from '../../api/client/prompts';
import { MonoBadge, StatusBadge, Tag } from './PromptBadges';

interface Props {
  prompts: PromptItem[];
  onSelect: (row: PromptItem) => void;
}

export default function PromptGrid({ prompts, onSelect }: Props) {
  return (
    <div className="grid gap-3.5 [grid-template-columns:repeat(auto-fill,minmax(300px,1fr))]">
      {prompts.map((p) => (
        <button
          key={p.id}
          onClick={() => onSelect(p)}
          className="text-left bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[14px] p-[18px] pb-3.5 cursor-pointer transition-all hover:border-[var(--color-border-strong)] hover:-translate-y-0.5 hover:shadow-[0_8px_32px_rgba(0,0,0,0.25)]"
        >
          <div className="flex items-center justify-between mb-2.5">
            <span className="text-sm font-semibold text-[var(--color-text-primary)] truncate pr-2">
              {p.name}
            </span>
            <StatusBadge status={p.status} />
          </div>
          <p className="m-0 mb-3 text-[12.5px] leading-[1.5] text-[var(--color-text-secondary)] line-clamp-2 min-h-[38px]">
            {p.description || '暂无描述'}
          </p>
          <div className="flex items-center justify-between">
            <div className="flex gap-1 flex-wrap">
              {(p as unknown as { tags?: string[] }).tags ? (
                ((p as unknown as { tags: string[] }).tags as string[]).map(
                  (tag) => <Tag key={tag}>{tag}</Tag>,
                )
              ) : (
                <Tag>{p.category}</Tag>
              )}
              <MonoBadge>{p.version}</MonoBadge>
            </div>
            <span className="text-[11px] font-mono text-[var(--color-text-tertiary)]">
              {((p as unknown as { uses?: number }).uses ?? 0).toLocaleString()}{' '}
              次调用
            </span>
          </div>
        </button>
      ))}
    </div>
  );
}
