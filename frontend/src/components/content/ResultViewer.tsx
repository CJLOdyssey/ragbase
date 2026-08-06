import { useState } from 'react';
import { Image, Wand2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { GenerationDetail } from '../../types/generation';

interface GenerationResult {
  title?: string;
  summary?: string;
  body_markdown?: string;
  keywords?: string[];
}

interface ResultViewerProps {
  detail: GenerationDetail;
  busy: 'variants' | 'image' | null;
  onGenerateVariants: () => void;
  onGenerateImage: (prompt: string, provider: string) => void;
  onCompose: () => void;
}

const IMAGE_PROVIDERS = ['openai', 'dashscope', 'stability'];

export default function ResultViewer({
  detail,
  busy,
  onGenerateVariants,
  onGenerateImage,
  onCompose,
}: ResultViewerProps) {
  const { t } = useTranslation();
  const result = (detail.result ?? {}) as GenerationResult;
  const [prompt, setPrompt] = useState('');
  const [provider, setProvider] = useState(IMAGE_PROVIDERS[0]);

  return (
    <section
      aria-label={t('content.result.bodyLabel')}
      className="bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--da-input-radius)] p-5 flex flex-col gap-4"
    >
      <div>
        <h2 className="text-sm font-medium text-[var(--color-text-muted)] mb-1">
          {t('content.result.titleLabel')}
        </h2>
        <p className="text-base font-semibold text-[var(--color-text-primary)]">
          {result.title || '—'}
        </p>
      </div>

      <div>
        <h2 className="text-sm font-medium text-[var(--color-text-muted)] mb-1">
          {t('content.result.summaryLabel')}
        </h2>
        <p className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap">
          {result.summary || '—'}
        </p>
      </div>

      <div>
        <h2 className="text-sm font-medium text-[var(--color-text-muted)] mb-1">
          {t('content.result.bodyLabel')}
        </h2>
        <pre className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap font-sans leading-relaxed">
          {result.body_markdown || '—'}
        </pre>
      </div>

      <div className="flex flex-col gap-3 border-t border-[var(--color-border)] pt-4">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={onGenerateVariants}
            disabled={busy !== null}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium bg-[var(--color-accent)] text-[var(--color-text-on-accent)] cursor-pointer hover:brightness-115 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <Wand2 size={14} />
            <span>{t('content.variants.generateVariant')}</span>
          </button>
          <button
            type="button"
            onClick={onCompose}
            disabled={busy !== null}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium bg-[var(--color-surface-hover)] text-[var(--color-text-primary)] cursor-pointer hover:bg-[var(--color-border)] disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <Image size={14} />
            <span>{t('content.card.compose')}</span>
          </button>
        </div>
        <p className="text-xs text-[var(--color-text-muted)]">
          {t('content.variants.limit', { count: 3 })}
        </p>

        <div className="flex flex-wrap items-center gap-2">
          <input
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={t('content.image.promptPlaceholder')}
            maxLength={1000}
            aria-label={t('content.image.prompt')}
            className="flex-1 min-w-[220px] bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]"
          />
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            aria-label={t('content.image.prompt')}
            className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl px-2 py-2 text-sm text-[var(--color-text-primary)]"
          >
            {IMAGE_PROVIDERS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => onGenerateImage(prompt, provider)}
            disabled={busy !== null || !prompt.trim()}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium bg-[var(--color-surface-hover)] text-[var(--color-text-primary)] cursor-pointer hover:bg-[var(--color-border)] disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <span>
              {busy === 'image'
                ? t('content.image.generating')
                : t('content.image.generate')}
            </span>
          </button>
        </div>

        {busy === 'variants' && (
          <p role="status" className="text-xs text-[var(--color-text-muted)]">
            {t('content.variants.generating')}
          </p>
        )}
      </div>
    </section>
  );
}
