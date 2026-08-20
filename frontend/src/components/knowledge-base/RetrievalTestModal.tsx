import { useState } from 'react';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import Modal from '../shared/Modal';
import { useMutation } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  testRetrieval,
  type RetrievalTestResult,
} from '../../api/client/ragTest';

interface Props {
  knowledgeBaseId: string;
  knowledgeBaseName: string;
  onClose: () => void;
}

export default function RetrievalTestModal({
  knowledgeBaseId,
  knowledgeBaseName,
  onClose,
}: Props) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [rewrite, setRewrite] = useState(false);
  const [result, setResult] = useState<RetrievalTestResult | null>(null);

  const testMutation = useMutation({
    mutationFn: testRetrieval,
    onSuccess: (data) => setResult(data),
  });

  const run = () => {
    const q = query.trim();
    if (!q) return;
    testMutation.mutate({
      query: q,
      topK,
      rewrite,
      knowledgeBaseId,
    });
  };

  return (
    <Modal
      title={`${t('ragTest.title')} · ${knowledgeBaseName}`}
      onClose={onClose}
      ariaLabel={t('ragTest.title')}
      width={640}
      bodyClassName="p-6 flex flex-col gap-4"
      footer={
        <>
          <button
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]"
            onClick={onClose}
          >
            {t('confirm.cancel')}
          </button>
          <button
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none bg-[var(--color-accent)] text-white hover:opacity-90 disabled:opacity-60"
            onClick={run}
            disabled={!query.trim() || testMutation.isPending}
          >
            <Search size={14} />
            {testMutation.isPending ? t('ragTest.running') : t('ragTest.run')}
          </button>
        </>
      }
    >
      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-[var(--color-text-primary)]">
          {t('ragTest.queryLabel')}
        </label>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') run();
          }}
          placeholder={t('ragTest.queryPlaceholder')}
          className="w-full px-3 py-2 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-accent)]"
        />
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-sm text-[var(--color-text-secondary)]">
            {t('ragTest.topK')}
          </label>
          <select
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            className="px-2 py-1 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] outline-none cursor-pointer"
          >
            {[1, 3, 5, 10].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)] cursor-pointer">
          <input
            type="checkbox"
            checked={rewrite}
            onChange={(e) => setRewrite(e.target.checked)}
            className="accent-[var(--color-accent)]"
          />
          {t('ragTest.rewrite')}
        </label>
      </div>

      {testMutation.isPending && <LoadingState centered={true} />}

      {testMutation.isError && (
        <p className="text-sm text-[var(--color-danger, #dc2626)] m-0">
          {t('monitoring.loadFailed')}
        </p>
      )}

      {result && !testMutation.isPending && (
        <div className="flex flex-col gap-2">
          {result.hitCount > 0 && (
            <div className="text-sm text-[var(--color-text-secondary)]">
              {t('ragTest.hits', { count: result.hitCount })}
            </div>
          )}
          {result.hitCount === 0 && (
            <EmptyState
              icon={<Search size={24} />}
              title={t('ragTest.noHits')}
              description={
                result.embeddingConfigured
                  ? t('ragTest.emptyHint')
                  : t('ragTest.embeddingNotConfigured')
              }
            />
          )}
          {result.sources.map((s, i) => (
            <div
              key={`${s.assetId ?? 'chunk'}-${i}`}
              className="flex flex-col gap-1 p-3 rounded-lg bg-[var(--color-surface)]"
            >
              <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
                <span className="text-[var(--color-accent)] font-medium">
                  {(s.similarity * 100).toFixed(0)}%
                </span>
                <span className="truncate">
                  {s.assetName ?? t('ragTest.source')}
                </span>
              </div>
              <p className="text-sm text-[var(--color-text-primary)] m-0 line-clamp-3">
                {s.text}
              </p>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}
