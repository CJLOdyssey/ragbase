import { useState } from 'react';
import EmptyState from '../shared/EmptyState';
import { useMutation } from '@tanstack/react-query';
import { Input, InputNumber, Modal, Switch } from 'antd';
import { Search } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  testRetrieval,
  type RetrievalTestResult,
} from '../../api/client/ragTest';

export interface KbRecallModalProps {
  open: boolean;
  knowledgeBaseId: string;
  knowledgeBaseName: string;
  onClose: () => void;
}

export default function KbRecallModal({
  open,
  knowledgeBaseId,
  knowledgeBaseName,
  onClose,
}: KbRecallModalProps) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [threshold, setThreshold] = useState(0.75);
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

  const shown = result?.sources.filter((s) => s.similarity >= threshold) ?? [];
  const canRun = query.trim().length > 0 && !testMutation.isPending;

  return (
    <Modal
      title={`${t('ragTest.title')} · ${knowledgeBaseName}`}
      open={open}
      onCancel={onClose}
      centered
      width={640}
      footer={null}
      styles={{ body: { padding: 20, maxHeight: '65vh', overflowY: 'auto' } }}
    >
      <div className="flex flex-col gap-4">
        <section>
          <label className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]">
            {t('ragTest.queryLabel')}
          </label>
          <Input.TextArea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onPressEnter={(e) => {
              e.preventDefault();
              run();
            }}
            rows={3}
            placeholder={t('ragTest.queryPlaceholder')}
            className="!bg-[var(--color-surface)] !border-[var(--color-border)] !text-[var(--color-text-primary)] resize-none"
          />
          <div className="mt-3 grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-[var(--color-text-secondary)]">
                Top K
              </label>
              <InputNumber
                min={1}
                max={50}
                value={topK}
                onChange={(v) => setTopK(typeof v === 'number' ? v : 5)}
                className="!w-full !bg-[var(--color-surface)] !border-[var(--color-border)]"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-[var(--color-text-secondary)]">
                {t('kb.similarityThreshold')}
              </label>
              <InputNumber
                min={0}
                max={1}
                step={0.05}
                value={threshold}
                onChange={(v) => setThreshold(typeof v === 'number' ? v : 0.75)}
                className="!w-full !bg-[var(--color-surface)] !border-[var(--color-border)]"
              />
            </div>
          </div>
          <label className="mt-3 flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
            <Switch size="small" checked={rewrite} onChange={setRewrite} />
            {t('ragTest.rewrite')}
          </label>
          <button
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md bg-[var(--color-accent)] px-3 py-2 text-sm font-medium text-[var(--color-text-on-accent)] transition-opacity hover:opacity-90 disabled:opacity-60"
            onClick={run}
            disabled={!canRun}
          >
            <Search size={14} />
            {testMutation.isPending ? t('ragTest.running') : t('ragTest.run')}
          </button>
        </section>

        <section>
          <div className="mb-2 text-sm font-medium text-[var(--color-text-primary)]">
            {t('kb.recallResults')}
          </div>

          <RecallResults
            isPending={testMutation.isPending}
            isError={testMutation.isError}
            result={result}
            shown={shown}
          />
        </section>
      </div>
    </Modal>
  );
}

function RecallResults({
  isPending,
  isError,
  result,
  shown,
}: {
  isPending: boolean;
  isError: boolean;
  result: RetrievalTestResult | null;
  shown: RetrievalTestResult['sources'];
}) {
  const { t } = useTranslation();
  if (isPending) {
    return (
      <div className="py-8 text-center text-sm text-[var(--color-text-muted)]">
        {t('ragTest.running')}
      </div>
    );
  }
  if (isError) {
    return (
      <p className="m-0 text-sm text-[var(--color-danger)]">
        {t('monitoring.loadFailed')}
      </p>
    );
  }
  if (!result) {
    return (
      <div className="py-10 text-center text-[var(--color-text-muted)]">
        <div className="mb-2 text-2xl">◈</div>
        <div className="text-sm">{t('kb.recallEmptyPrompt')}</div>
      </div>
    );
  }
  if (shown.length === 0) {
    return (
      <EmptyState
        icon={<Search size={24} />}
        title={t('ragTest.noHits')}
        description={
          result.embeddingConfigured
            ? t('ragTest.emptyHint')
            : t('ragTest.embeddingNotConfigured')
        }
      />
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <div className="text-sm text-[var(--color-text-secondary)]">
        {t('ragTest.hits', { count: shown.length })}
      </div>
      {shown.map((s, i) => (
        <div
          key={`${s.assetId ?? 'chunk'}-${i}`}
          className="flex flex-col gap-1 rounded-lg bg-[var(--color-surface)] p-3"
        >
          <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
            <span className="font-medium text-[var(--color-accent)]">
              {(s.similarity * 100).toFixed(0)}%
            </span>
            <span className="truncate">
              {s.assetName ?? t('ragTest.source')}
            </span>
          </div>
          <p className="m-0 text-sm text-[var(--color-text-primary)] line-clamp-3">
            {s.text}
          </p>
        </div>
      ))}
    </div>
  );
}
