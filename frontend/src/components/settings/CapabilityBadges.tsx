import { useTranslation } from 'react-i18next';
import { CAPABILITY_BADGE_KEYS } from '../../utils/providerCategories';

const STYLES: Record<string, string> = {
  llm: 'bg-blue-500/15 text-blue-400',
  embedding: 'bg-purple-500/15 text-purple-400',
  rerank: 'bg-cyan-500/15 text-cyan-400',
  speech2text: 'bg-orange-500/15 text-orange-400',
  tts: 'bg-pink-500/15 text-pink-400',
  moderation: 'bg-yellow-500/15 text-yellow-400',
  tool: 'bg-green-500/15 text-green-400',
};

export default function CapabilityBadges({
  capabilities,
}: {
  capabilities: string[];
}) {
  const { t } = useTranslation();
  if (!capabilities || capabilities.length === 0)
    return <span className="text-[var(--color-text-muted)]">—</span>;
  return (
    <span className="flex flex-wrap gap-1">
      {capabilities.map((c) => (
        <span
          key={c}
          className={`px-1.5 py-0.5 rounded text-xs ${STYLES[c] ?? 'bg-[var(--color-surface-hover)]'}`}
        >
          {t(CAPABILITY_BADGE_KEYS[c] ?? c)}
        </span>
      ))}
    </span>
  );
}
