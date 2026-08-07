import { useMemo, useState } from 'react';
import { AlertCircle, Search } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface ModelEntry {
  model: string;
  keyId: string;
  keyLabel?: string;
  /** 模型能力标签 —— 由后端提供，当前预留 */
  capabilities?: ('vision' | 'tool_calling' | 'reasoning' | 'image')[];
  /** 上下文窗口 —— 由后端提供，当前预留 */
  contextWindow?: number;
}

interface Props {
  models: ModelEntry[];
  selectedModel: string;
  onSelect: (model: string) => void;
}

export default function ModelSelector({
  models,
  selectedModel,
  onSelect,
}: Props) {
  const { t } = useTranslation();
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    if (!search.trim()) return models;
    const q = search.toLowerCase();
    return models.filter((m) => m.model.toLowerCase().includes(q));
  }, [models, search]);

  return (
    <div className="h-full min-h-0 flex flex-col">
      <div className="flex items-center justify-between mb-4 shrink-0">
        <h4>{t('api.defaultModel')}</h4>
      </div>
      <div className="relative mb-4 shrink-0">
        <Search
          size={14}
          className="absolute text-[var(--color-text-muted)] pointer-events-none"
          style={{
            left: 12,
            top: '50%',
            transform: 'translateY(-50%)',
            zIndex: 10,
          }}
        />
        <input
          type="text"
          placeholder="搜索模型名称..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full py-2 pr-3 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-md text-sm text-[var(--color-text-primary)] outline-none transition-colors focus:border-[var(--color-accent)] placeholder:text-[var(--color-text-muted)]"
          style={{ paddingLeft: 36 }}
        />
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-2">
        {filtered.map(({ model, keyLabel }) => (
          <label
            key={model}
            className="flex items-center gap-3 p-3 rounded-md cursor-pointer transition-[background] duration-150 hover:bg-[var(--color-surface-hover)]"
          >
            <input
              type="radio"
              name="defaultModel"
              value={model}
              checked={selectedModel === model}
              onChange={() => onSelect(model)}
              className="shrink-0"
            />
            <div className="flex flex-col min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm text-[var(--color-text-primary)] font-mono font-medium">
                  {model}
                </span>
              </div>
              {keyLabel && (
                <span className="text-xs text-[var(--color-text-muted)] mt-0.5 truncate">
                  {keyLabel}
                </span>
              )}
            </div>
          </label>
        ))}
        {filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-[var(--color-text-muted)] text-center gap-2">
            <AlertCircle size={28} className="opacity-30" />
            <p className="text-sm">
              {search ? '没有匹配的模型' : t('api.noKeys')}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
