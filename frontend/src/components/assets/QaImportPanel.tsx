import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Input } from 'antd';
import { Plus, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { addQaChunks, type QAPair } from '../../api/client/assets';

interface QaImportPanelProps {
  assetId: string;
  onDone: () => void;
}

interface Row {
  key: number;
  question: string;
  answer: string;
}

let rowSeq = 0;

/** Bulk curated-QA importer — one vector chunk per question/answer pair. */
export default function QaImportPanel({ assetId, onDone }: QaImportPanelProps) {
  const { t } = useTranslation();
  const [rows, setRows] = useState<Row[]>([
    { key: 0, question: '', answer: '' },
  ]);
  const [error, setError] = useState<string | null>(null);

  const validRows: QAPair[] = rows
    .map(({ question, answer }) => ({
      question: question.trim(),
      answer: answer.trim(),
    }))
    .filter((p) => p.question && p.answer);

  const importMutation = useMutation({
    mutationFn: () => addQaChunks(assetId, validRows),
    onSuccess: () => onDone(),
    onError: () => setError(t('assets.chunks.qa.importFailed')),
  });

  const update = (key: number, patch: Partial<Row>) =>
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...patch } : r)));

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs text-[var(--color-text-muted)] m-0">
        {t('assets.chunks.qa.hint')}
      </p>

      {rows.map((row) => (
        <div
          key={row.key}
          className="flex flex-col gap-1.5 rounded-lg border border-[var(--color-border)] p-3"
          data-testid={`qa-row-${row.key}`}
        >
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-[var(--color-text-tertiary)]">
              Q
            </span>
            <Input
              value={row.question}
              onChange={(e) => update(row.key, { question: e.target.value })}
              placeholder={t('assets.chunks.qa.questionPlaceholder')}
              maxLength={500}
            />
            <button
              type="button"
              aria-label={t('assets.chunks.qa.removeRow')}
              disabled={rows.length === 1}
              onClick={() =>
                setRows((rs) => rs.filter((r) => r.key !== row.key))
              }
              className="bg-transparent border-none cursor-pointer p-1 rounded text-[var(--color-text-muted)] hover:text-[var(--color-danger)] disabled:opacity-40"
            >
              <Trash2 size={13} />
            </button>
          </div>
          <Input.TextArea
            value={row.answer}
            onChange={(e) => update(row.key, { answer: e.target.value })}
            placeholder={t('assets.chunks.qa.answerPlaceholder')}
            maxLength={4000}
            rows={2}
          />
        </div>
      ))}

      <div className="flex items-center justify-between">
        <button
          type="button"
          disabled={rows.length >= 50}
          onClick={() =>
            setRows((rs) => [
              ...rs,
              { key: ++rowSeq, question: '', answer: '' },
            ])
          }
          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-md border border-[var(--color-border)] bg-transparent text-[var(--color-text-secondary)] cursor-pointer disabled:opacity-50"
        >
          <Plus size={12} />
          {t('assets.chunks.qa.addRow')}
        </button>
        <button
          type="button"
          disabled={validRows.length === 0 || importMutation.isPending}
          onClick={() => importMutation.mutate()}
          className="px-3 py-1.5 text-xs rounded-md border-none bg-[var(--color-accent)] text-white cursor-pointer disabled:opacity-50"
        >
          {importMutation.isPending
            ? t('assets.chunks.qa.importing')
            : t('assets.chunks.qa.import', { count: validRows.length })}
        </button>
      </div>

      {error && (
        <p className="text-xs text-[var(--color-danger)] m-0">{error}</p>
      )}
    </div>
  );
}
