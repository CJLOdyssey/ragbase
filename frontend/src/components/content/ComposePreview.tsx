import { useCallback, useEffect, useState } from 'react';
import Modal from '../shared/Modal';
import { useTranslation } from 'react-i18next';
import type {
  ComposeCardResult,
  ComposeTemplate,
} from '../../types/generation';
import { listComposeTemplates } from '../../api/client/composeTemplates';
import { composeCard } from '../../api/client/generations';
import { useToast } from '../../utils/useToast';

interface ComposePreviewProps {
  runId: string;
  defaultTitle: string;
  defaultSummary: string;
  onClose: () => void;
}

export default function ComposePreview({
  runId,
  defaultTitle,
  defaultSummary,
  onClose,
}: ComposePreviewProps) {
  const { t } = useTranslation();
  const { toast } = useToast();
  const [templates, setTemplates] = useState<ComposeTemplate[]>([]);
  const [templateId, setTemplateId] = useState('');
  const [title, setTitle] = useState(defaultTitle);
  const [summary, setSummary] = useState(defaultSummary);
  const [composing, setComposing] = useState(false);
  const [result, setResult] = useState<ComposeCardResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    void listComposeTemplates().then((list) => {
      if (cancelled) return;
      setTemplates(list);
      const def = list.find((tmpl) => tmpl.is_default) ?? list[0];
      if (def) setTemplateId(def.id);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleCompose = useCallback(async () => {
    if (!templateId || composing) return;
    setComposing(true);
    try {
      setResult(await composeCard(runId, { templateId, title, summary }));
    } catch {
      toast(t('assets.upload.failed'), 'error');
    } finally {
      setComposing(false);
    }
  }, [templateId, title, summary, runId, composing, toast, t]);

  const footer = (
    <button
      type="button"
      onClick={() => void handleCompose()}
      disabled={!templateId || composing}
      className="px-5 py-2 rounded-xl text-sm font-semibold bg-[var(--color-accent)] text-[var(--color-text-on-accent)] cursor-pointer hover:brightness-115 disabled:opacity-60 disabled:cursor-not-allowed"
    >
      {t('content.card.compose')}
    </button>
  );

  return (
    <Modal
      title={t('content.card.compose')}
      onClose={onClose}
      footer={footer}
      ariaLabel={t('content.card.compose')}
    >
      <div className="flex flex-col gap-4">
        <div>
          <label className="text-sm font-medium text-[var(--color-text-muted)] mb-1 block">
            {t('content.card.template')}
          </label>
          <select
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value)}
            aria-label={t('content.card.selectTemplate')}
            className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl px-3 py-2 text-sm text-[var(--color-text-primary)]"
          >
            {templates.length === 0 && (
              <option value="">{t('content.card.selectTemplate')}</option>
            )}
            {templates.map((tmpl) => (
              <option key={tmpl.id} value={tmpl.id}>
                {tmpl.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="compose-title"
            className="text-sm font-medium text-[var(--color-text-muted)] mb-1 block"
          >
            {t('content.card.titleLabel')}
          </label>
          <input
            id="compose-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl px-3 py-2 text-sm text-[var(--color-text-primary)]"
          />
        </div>

        <div>
          <label
            htmlFor="compose-summary"
            className="text-sm font-medium text-[var(--color-text-muted)] mb-1 block"
          >
            {t('content.card.summaryLabel')}
          </label>
          <textarea
            id="compose-summary"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            rows={3}
            className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl px-3 py-2 text-sm text-[var(--color-text-primary)]"
          />
        </div>

        {result && (
          <div
            data-testid="compose-result"
            className="border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-surface)]"
          >
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-2">
              {t('content.card.preview')} · {result.template.name}
            </h3>
            <p className="text-sm text-[var(--color-text-primary)] mb-1">
              <span className="text-[var(--color-text-muted)]">
                {t('content.card.titleLabel')}:
              </span>{' '}
              {result.fields.title}
            </p>
            <p className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap">
              <span className="text-[var(--color-text-muted)]">
                {t('content.card.summaryLabel')}:
              </span>{' '}
              {result.fields.summary}
            </p>
          </div>
        )}
      </div>
    </Modal>
  );
}
