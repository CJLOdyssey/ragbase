import { useCallback, useEffect, useState } from 'react';
import { Loader2, Square } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { GenerationDetail } from '../../types/generation';
import {
  createGeneration,
  createVariations,
  generateImage,
  getGeneration,
} from '../../api/client/generations';
import AssetPicker from './AssetPicker';
import ComposePreview from './ComposePreview';
import ResultViewer from './ResultViewer';

const CONTENT_TYPES = [
  'xiaohongshu',
  'wechat',
  'shortvideo',
  'marketing',
  'generic',
] as const;

const POLL_INTERVAL_MS = 2000;

export default function ComposerPage() {
  const { t } = useTranslation();
  const [contentType, setContentType] = useState<string>(CONTENT_TYPES[0]);
  const [topic, setTopic] = useState('');
  const [extra, setExtra] = useState('');
  const [assetIds, setAssetIds] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [detail, setDetail] = useState<GenerationDetail | null>(null);
  const [busy, setBusy] = useState<'variants' | 'image' | null>(null);
  const [composeOpen, setComposeOpen] = useState(false);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const d = await getGeneration(runId);
        if (cancelled) return;
        setDetail(d);
        if (d.status === 'completed' || d.status === 'error') {
          setRunId(null);
          setRunning(false);
        }
      } catch {
        if (cancelled) return;
        setRunId(null);
        setRunning(false);
      }
    };
    void poll();
    const timer = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [runId]);

  const stop = useCallback(() => {
    setRunId(null);
    setRunning(false);
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!topic.trim() || running) return;
    setRunning(true);
    setDetail(null);
    setBusy(null);
    try {
      const resp = await createGeneration({
        contentType,
        generationMode: 'generate',
        topic: topic.trim(),
        additionalRequirements: extra.trim() || undefined,
        assetIds,
      });
      setRunId(resp.run_id);
    } catch {
      setRunning(false);
    }
  }, [topic, extra, contentType, assetIds, running]);

  const handleVariants = useCallback(async () => {
    if (!detail || busy) return;
    setBusy('variants');
    try {
      const resp = await createVariations(detail.id);
      setRunId(resp.run_id);
      setRunning(true);
    } catch {
      setBusy(null);
    }
  }, [detail, busy]);

  const handleImage = useCallback(
    async (prompt: string, provider: string) => {
      if (!detail || busy || !prompt.trim()) return;
      setBusy('image');
      try {
        await generateImage(detail.id, { prompt: prompt.trim(), provider });
      } catch {
        setBusy(null);
      }
    },
    [detail, busy],
  );

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-[900px] mx-auto px-6 py-8">
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)] mb-6">
          {t('content.title')}
        </h1>

        <div className="flex flex-col gap-5">
          <fieldset>
            <legend className="text-sm font-medium text-[var(--color-text-muted)] mb-2">
              {t('content.input.contentTypeLabel')}
            </legend>
            <div className="flex flex-wrap gap-2">
              {CONTENT_TYPES.map((ct) => (
                <button
                  key={ct}
                  type="button"
                  onClick={() => setContentType(ct)}
                  aria-pressed={contentType === ct}
                  className={`px-4 py-2 rounded-xl text-sm border transition-colors ${
                    contentType === ct
                      ? 'bg-[var(--color-accent)] text-[var(--color-text-on-accent)] border-transparent'
                      : 'bg-[var(--color-surface-raised)] text-[var(--color-text-primary)] border-[var(--color-border)] hover:bg-[var(--color-surface-hover)]'
                  }`}
                >
                  {t(`content.contentType_${ct}`)}
                </button>
              ))}
            </div>
          </fieldset>

          <fieldset>
            <legend className="text-sm font-medium text-[var(--color-text-muted)] mb-2">
              {t('content.input.generationModeLabel')}
            </legend>
            <div className="flex items-center gap-2 text-sm text-[var(--color-text-primary)]">
              <input
                type="radio"
                name="generationMode"
                id="generationMode-single"
                checked
                readOnly
              />
              <label htmlFor="generationMode-single">
                {t('content.generationMode_single')}
              </label>
            </div>
          </fieldset>

          <textarea
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder={t('content.input.topicPlaceholder')}
            maxLength={500}
            aria-label={t('content.input.topicPlaceholder')}
            className="w-full bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--da-input-radius)] px-4 py-3 text-base text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] min-h-[72px]"
          />

          <textarea
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
            placeholder={t('content.input.extraPlaceholder')}
            maxLength={2000}
            aria-label={t('content.input.extraLabel')}
            className="w-full bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--da-input-radius)] px-4 py-3 text-base text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] min-h-[56px]"
          />

          <AssetPicker selected={assetIds} onChange={setAssetIds} />

          <div className="flex justify-end">
            {running ? (
              <button
                type="button"
                onClick={stop}
                className="flex items-center justify-center gap-2 px-6 py-2 rounded-xl border-none text-base font-semibold cursor-pointer min-h-10 bg-red-500/20 text-[var(--color-danger)] hover:bg-red-500/30"
              >
                <Square size={14} fill="currentColor" />
                <span>{t('content.stop')}</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={handleGenerate}
                disabled={!topic.trim()}
                className={`flex items-center justify-center gap-2 px-6 py-2 rounded-xl border-none text-base font-semibold min-h-10 ${
                  topic.trim()
                    ? 'bg-[var(--color-accent)] text-[var(--color-text-on-accent)] cursor-pointer hover:brightness-115'
                    : 'bg-[var(--color-surface-hover)] text-[var(--color-text-muted)] cursor-not-allowed opacity-70'
                }`}
              >
                <span>{t('content.generate')}</span>
              </button>
            )}
          </div>

          {running && (
            <p
              role="status"
              className="flex items-center gap-2 text-sm text-[var(--color-text-muted)]"
            >
              <Loader2 size={16} className="animate-spin" />
              {t('content.generating')}
            </p>
          )}

          {detail && detail.status === 'completed' && (
            <ResultViewer
              detail={detail}
              busy={busy}
              onGenerateVariants={handleVariants}
              onGenerateImage={handleImage}
              onCompose={() => setComposeOpen(true)}
            />
          )}
        </div>
      </div>

      {composeOpen && detail && (
        <ComposePreview
          runId={detail.id}
          defaultTitle={
            (detail.result as { title?: string } | undefined)?.title ?? ''
          }
          defaultSummary={
            (detail.result as { summary?: string } | undefined)?.summary ?? ''
          }
          onClose={() => setComposeOpen(false)}
        />
      )}
    </div>
  );
}
