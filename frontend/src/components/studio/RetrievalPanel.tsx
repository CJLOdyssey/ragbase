import { memo, useMemo } from 'react';
import { FileText, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { RagSource } from '../../types';

interface Props {
  sources: RagSource[];
  isOpen: boolean;
  onClose: () => void;
}

function getSimilarityColor(similarity: number | undefined): string {
  if (typeof similarity !== 'number') return 'var(--color-text-muted)';
  const pct = similarity * 100;
  if (pct >= 80) return 'var(--color-success, #10b981)';
  if (pct >= 60) return 'var(--color-warning, #f59e0b)';
  return 'var(--color-danger, #ef4444)';
}

function highlightFirst(text: string): string {
  if (!text) return '';
  // Bold the first sentence or first ~40 chars as a "key term"
  const match = text.match(/^[^.!?\n]+[.!?]?/);
  const head = match ? match[0].trim() : text.slice(0, 40);
  if (!head) return text;
  const idx = text.indexOf(head);
  if (idx < 0) return text;
  const before = text.slice(0, idx);
  const after = text.slice(idx + head.length);
  return `${before}**${head}**${after}`;
}

const RetrievalPanel = memo(function RetrievalPanel({
  sources,
  isOpen,
  onClose,
}: Props) {
  const { t } = useTranslation();

  const sortedSources = useMemo(() => {
    return [...sources].sort((a, b) => {
      const sa = typeof a.similarity === 'number' ? a.similarity : -1;
      const sb = typeof b.similarity === 'number' ? b.similarity : -1;
      return sb - sa;
    });
  }, [sources]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[1000] flex justify-end"
      data-testid="retrieval-panel-backdrop"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/30" />
      <div
        className="relative w-[400px] max-w-[90vw] h-full bg-[var(--color-surface)] border-l border-[var(--color-border)] shadow-xl flex flex-col animate-[slideInRight_0.2s_ease-out]"
        onClick={(e) => e.stopPropagation()}
        data-testid="retrieval-panel"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)] shrink-0">
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)] m-0">
            {t('retrievalPanel.title', { count: sources.length })}
          </h2>
          <button
            className="flex items-center justify-center w-7 h-7 bg-transparent border-none rounded-md text-[var(--color-text-muted)] cursor-pointer hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]"
            onClick={onClose}
            aria-label={t('common.close')}
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto min-h-0 p-4">
          {sortedSources.length === 0 ? (
            <div className="flex items-center justify-center h-full text-sm text-[var(--color-text-muted)]">
              {t('common.noData')}
            </div>
          ) : (
            <ul className="flex flex-col gap-3 m-0 p-0 list-none">
              {sortedSources.map((s, i) => (
                <li
                  key={`${s.asset_id ?? s.asset_name ?? 'src'}-${i}`}
                  className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-3"
                  data-testid="retrieval-source-card"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <FileText
                      size={14}
                      className="text-[var(--color-text-muted)] shrink-0"
                    />
                    <span className="flex-1 min-w-0 text-sm font-medium text-[var(--color-text-primary)] truncate">
                      {s.asset_name || t('teamMessage.sourceAsset')}
                    </span>
                    {typeof s.similarity === 'number' && (
                      <span
                        className="text-xs font-medium px-1.5 py-0.5 rounded-full shrink-0"
                        style={{
                          color: getSimilarityColor(s.similarity),
                          backgroundColor: `${getSimilarityColor(s.similarity)}20`,
                        }}
                        data-testid="similarity-badge"
                      >
                        {Math.round(s.similarity * 100)}%
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-[var(--color-text-secondary)] leading-relaxed whitespace-pre-wrap">
                    {highlightFirst(s.text)}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
});

export default RetrievalPanel;
