import { FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import type { KnowledgeBase } from '../../api/client/knowledgeBases';

interface UncategorizedSectionProps {
  assets: AssetItem[];
  kbs: KnowledgeBase[];
  onAssign: (assetId: string, kbId: string | null) => void;
}

export default function UncategorizedSection({
  assets,
  kbs,
  onAssign,
}: UncategorizedSectionProps) {
  const { t } = useTranslation();
  if (assets.length === 0) return null;

  return (
    <section className="mt-8">
      <h2 className="mb-3 text-sm font-medium text-[var(--color-text-secondary)]">
        {t('kb.uncategorized')}
      </h2>
      <div className="flex flex-col gap-2">
        {assets.map((asset) => (
          <div
            key={asset.id}
            className="flex items-center gap-3 rounded-lg bg-[var(--color-surface-raised)] px-4 py-2"
          >
            <FileText
              size={16}
              className="shrink-0 text-[var(--color-text-muted)]"
            />
            <span className="flex-1 truncate text-sm text-[var(--color-text-primary)]">
              {asset.name}
            </span>
            <select
              aria-label={`${t('kb.assignTo')} ${asset.name}`}
              className="cursor-pointer rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 text-xs text-[var(--color-text-primary)] outline-none"
              value={asset.knowledgeBaseId ?? ''}
              onChange={(e) => {
                const kbId = e.target.value || null;
                onAssign(asset.id, kbId);
              }}
            >
              <option value="" disabled>
                {t('kb.assignTo')}
              </option>
              {kbs.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>
    </section>
  );
}
