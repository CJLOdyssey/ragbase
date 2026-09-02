import { useState } from 'react';
import EmptyState from '../shared/EmptyState';
import { useMutation } from '@tanstack/react-query';
import { Input, InputNumber, Modal, Select, Switch } from 'antd';
import { Search } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  testRetrieval,
  type RetrievalMethod,
  type RetrievalTestResult,
} from '../../api/client/ragTest';

export interface KbRecallModalProps {
  open: boolean;
  knowledgeBaseId: string;
  knowledgeBaseName: string;
  /** 该库已索引资产数 — 让用户知道测试的召回范围 */
  indexedCount: number;
  onClose: () => void;
}

export default function KbRecallModal({
  open,
  knowledgeBaseId,
  knowledgeBaseName,
  indexedCount,
  onClose,
}: KbRecallModalProps) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [threshold, setThreshold] = useState(0.75);
  const [rewrite, setRewrite] = useState(false);
  const [method, setMethod] = useState<RetrievalMethod>('hybrid');
  const [tagText, setTagText] = useState('');
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
      retrievalMethod: method,
      tags: tagText
        .split(/[,，]/)
        .map((t) => t.trim())
        .filter(Boolean),
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
      styles={{
        body: { padding: '20px 24px', maxHeight: '70vh', overflowY: 'auto' },
      }}
    >
      <div className="flex flex-col gap-4">
        {/* 召回范围提示 */}
        <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] px-3 py-2">
          <span className="text-xs text-[var(--color-text-muted)]">
            {t('kb.recallScope', { count: indexedCount })}
          </span>
        </div>

        {/* 查询输入区 */}
        <section>
          <label className="mb-2 block text-sm font-medium text-[var(--color-text-primary)]">
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
            className="!bg-[var(--color-surface)] !border-[var(--color-border)] !rounded-lg resize-none"
          />
        </section>

        {/* 参数配置区 */}
        <section className="flex flex-col gap-3">
          {/* 检索方式 + 标签过滤 */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-[var(--color-text-secondary)]">
                {t('ragTest.method')}
              </label>
              <Select
                value={method}
                onChange={(v) => setMethod(v)}
                options={[
                  { value: 'hybrid', label: t('ragTest.methodHybrid') },
                  { value: 'semantic', label: t('ragTest.methodSemantic') },
                  { value: 'lexical', label: t('ragTest.methodLexical') },
                ]}
                className="!rounded-lg"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-[var(--color-text-secondary)]">
                {t('ragTest.tagFilter')}
              </label>
              <Input
                value={tagText}
                onChange={(e) => setTagText(e.target.value)}
                placeholder={t('ragTest.tagFilterPlaceholder')}
                className="!rounded-lg"
              />
            </div>
          </div>
          {/* Top K + 相似度阈值 */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-[var(--color-text-secondary)]">
                Top K
              </label>
              <InputNumber
                min={1}
                max={50}
                value={topK}
                onChange={(v) => setTopK(typeof v === 'number' ? v : 5)}
                className="!w-full !rounded-lg"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-[var(--color-text-secondary)]">
                {t('kb.similarityThreshold')}
              </label>
              <InputNumber
                min={0}
                max={1}
                step={0.05}
                value={threshold}
                onChange={(v) => setThreshold(typeof v === 'number' ? v : 0.75)}
                className="!w-full !rounded-lg"
              />
            </div>
          </div>
          {/* 查询重写开关 */}
          <label className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)] cursor-pointer">
            <Switch size="small" checked={rewrite} onChange={setRewrite} />
            {t('ragTest.rewrite')}
          </label>
        </section>

        {/* 执行按钮 */}
        <button
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--color-accent)] px-4 py-2.5 text-sm font-medium text-[var(--color-text-on-accent)] transition-all hover:brightness-110 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:brightness-100"
          onClick={run}
          disabled={!canRun}
        >
          {testMutation.isPending ? (
            <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <Search size={14} />
          )}
          {testMutation.isPending ? t('ragTest.running') : t('ragTest.run')}
        </button>

        {/* 结果展示区 */}
        <section>
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
    <div className="flex flex-col gap-2.5">
      {shown.map((s, i) => (
        <div
          key={`${s.assetId ?? 'chunk'}-${i}`}
          className="group relative flex flex-col gap-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)] p-4 transition-all hover:border-[var(--color-border)] hover:shadow-sm"
        >
          {/* 头部：相似度 + 来源 */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center justify-center min-w-[48px] px-2 py-0.5 rounded-full text-xs font-semibold bg-[var(--color-accent)]/10 text-[var(--color-accent)]">
                {(s.similarity * 100).toFixed(0)}%
              </span>
              <span className="text-xs font-medium text-[var(--color-text-secondary)] truncate max-w-[200px]">
                {s.assetName ?? t('ragTest.source')}
              </span>
            </div>
            <span className="text-xs text-[var(--color-text-muted)]">
              #{i + 1}
            </span>
          </div>
          {/* 内容 */}
          <p className="m-0 text-sm leading-relaxed text-[var(--color-text-primary)] line-clamp-4">
            {s.text}
          </p>
        </div>
      ))}
    </div>
  );
}
