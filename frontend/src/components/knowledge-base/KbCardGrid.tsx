import { useTranslation } from 'react-i18next';
import type { KnowledgeBase } from '../../api/client/knowledgeBases';
import KbCard, { KB_ACCENTS } from './KbCard';
import { EMPTY_STAT, type KbStat } from './kbStats';

interface KbCardGridProps {
  kbs: KnowledgeBase[];
  perKb: Map<string, KbStat>;
  onCreate: () => void;
  onTest: (kb: KnowledgeBase) => void;
  onEdit: (kb: KnowledgeBase) => void;
  onDelete: (kb: KnowledgeBase) => void;
}

export default function KbCardGrid({
  kbs,
  perKb,
  onCreate,
  onTest,
  onEdit,
  onDelete,
}: KbCardGridProps) {
  const { t } = useTranslation();
  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(290px,1fr))] gap-3.5">
      {kbs.map((kb, idx) => {
        const s = perKb.get(kb.id) ?? EMPTY_STAT;
        const assetCount = kb.assetCount ?? s.assetCount;
        // 同 computeTotals 口径：assetCount 可能来自后端、indexed 来自前端
        // 列表，刷新时机不同会瞬时超 100%，收敛展示。
        const indexRate =
          assetCount > 0
            ? Math.min(100, Math.max(0, Math.round((s.indexedCount / assetCount) * 100)))
            : 0;
        return (
          <KbCard
            key={kb.id}
            kb={kb}
            accent={KB_ACCENTS[idx % KB_ACCENTS.length]}
            assetCount={assetCount}
            indexedCount={s.indexedCount}
            indexRate={indexRate}
            onTest={() => onTest(kb)}
            onEdit={() => onEdit(kb)}
            onDelete={() => onDelete(kb)}
          />
        );
      })}

      <button
        className="flex min-h-[220px] flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-[var(--color-border)] text-[var(--color-text-muted)] transition-colors hover:border-[color-mix(in_srgb,var(--color-accent)_40%,transparent)] hover:bg-[color-mix(in_srgb,var(--color-accent)_5%,transparent)]"
        onClick={onCreate}
      >
        <span className="text-2xl">+</span>
        <span className="text-sm">{t('kb.create')}</span>
      </button>
    </div>
  );
}
