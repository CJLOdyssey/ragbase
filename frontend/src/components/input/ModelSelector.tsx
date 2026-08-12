import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { ModelOption } from '../../types/input';

const RECENT_KEY = 'ragbase-recent-models';
const RECENT_LIMIT = 5;

function readRecentModels(): string[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed)
      ? parsed.filter((x): x is string => typeof x === 'string')
      : [];
  } catch {
    return [];
  }
}

function writeRecentModels(ids: string[]) {
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(ids));
  } catch {
    // storage unavailable — recent list applies for this session only
  }
}

interface Props {
  models: ModelOption[];
  selectedModel: string;
  onChange: (id: string) => void;
  /** Called when the user clicks the selector while no models are available */
  onConfigure?: () => void;
}

function ModelOptionButton({
  m,
  isSelected,
  isFocused,
  onSelect,
}: {
  m: ModelOption;
  isSelected: boolean;
  isFocused: boolean;
  onSelect: () => void;
}) {
  const { t } = useTranslation();
  const badge =
    m.status === 'deprecated' ? (
      <span className="text-xs px-1.5 py-0.5 rounded bg-[color-mix(in_srgb,var(--color-danger)_15%,transparent)] text-[var(--color-danger)]">
        {t('model.statusDeprecated')}
      </span>
    ) : m.status === 'sunset' ? (
      <span className="text-xs px-1.5 py-0.5 rounded bg-[color-mix(in_srgb,var(--color-danger)_15%,transparent)] text-[var(--color-danger)]">
        {t('model.statusSunset')}
      </span>
    ) : null;
  return (
    <button
      data-model-option
      className={`flex items-center justify-between w-full px-3 py-2 border-none rounded-md bg-transparent text-[var(--color-text-primary)] text-sm cursor-pointer transition-colors duration-100 text-left hover:bg-[var(--color-surface-hover)] ${isSelected ? 'bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)] text-[var(--color-accent)]' : ''} ${isFocused ? 'outline-2 outline-[var(--color-accent)] outline-offset-[-2px]' : ''}`}
      onClick={onSelect}
      role="option"
      aria-selected={isSelected}
      type="button"
    >
      <span>{m.label}</span>
      {badge}
    </button>
  );
}

function modelsReady(models: ModelOption[], selectedModel: string): boolean {
  return models.length > 0 || models.some((m) => m.id === selectedModel);
}

function SelectorLabel({
  hasLoadedOnce,
  isEmpty,
  current,
}: {
  hasLoadedOnce: boolean;
  isEmpty: boolean;
  current: ModelOption | undefined;
}) {
  const { t } = useTranslation();
  if (!hasLoadedOnce) {
    return (
      <span className="inline-flex items-center justify-center gap-1 h-[16px]">
        <Loader2 size={10} className="animate-spin" />
        <span>{t('model.loadingText')}</span>
      </span>
    );
  }
  return (
    <>
      {isEmpty ? t('model.configure') : (current?.label ?? t('model.select'))}
    </>
  );
}

function OptionsList({
  providers,
  recentModels,
  selectedModel,
  focusIdx,
  onSelect,
}: {
  providers: { title: string; items: ModelOption[] }[];
  recentModels: ModelOption[];
  selectedModel: string;
  focusIdx: number;
  onSelect: (id: string) => void;
}) {
  const { t } = useTranslation();
  const allOptions = [...recentModels, ...providers.flatMap((g) => g.items)];
  return (
    <>
      {recentModels.length > 0 && (
        <div key="__recent" className="flex flex-col">
          <div className="px-3 py-1.5 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">
            {t('model.recent')}
          </div>
          {recentModels.map((m) => (
            <ModelOptionButton
              key={m.id}
              m={m}
              isSelected={m.id === selectedModel}
              isFocused={allOptions.indexOf(m) === focusIdx}
              onSelect={() => onSelect(m.id)}
            />
          ))}
          <div className="h-px bg-[var(--color-border-subtle)] mx-2 my-1" />
        </div>
      )}
      {providers.map((g) => (
        <div key={g.title} className="flex flex-col">
          <div className="px-3 py-1.5 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
            {g.title}
          </div>
          {g.items.map((m) => (
            <ModelOptionButton
              key={m.id}
              m={m}
              isSelected={m.id === selectedModel}
              isFocused={allOptions.indexOf(m) === focusIdx}
              onSelect={() => onSelect(m.id)}
            />
          ))}
        </div>
      ))}
    </>
  );
}

export default function ModelSelector({
  models,
  selectedModel,
  onChange,
  onConfigure,
}: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [focusIdx, setFocusIdx] = useState(-1);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [recentIds, setRecentIds] = useState<string[]>(readRecentModels);
  const ref = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const current = models.find((m) => m.id === selectedModel);
  const isEmpty = models.length === 0;

  // Latch once models are available: render-phase state adjustment (React-sanctioned
  // pattern for deriving state from props). Prevents flashing "请配置API" on refresh.
  if (!hasLoadedOnce && modelsReady(models, selectedModel)) {
    setHasLoadedOnce(true);
  }

  // Fallback: if models never arrive after 4s, mark as loaded so "请配置API" shows.
  useEffect(() => {
    if (hasLoadedOnce) return;
    const timer = setTimeout(() => setHasLoadedOnce(true), 4000);
    return () => clearTimeout(timer);
  }, [hasLoadedOnce]);

  // Memoize grouped models — grouped by provider name.
  const groups = useMemo(() => {
    const g: Record<string, ModelOption[]> = {};
    for (const m of models) (g[m.provider] ??= []).push(m);
    return Object.entries(g).map(([provider, items]) => ({
      title: provider,
      items,
    }));
  }, [models]);

  // Recent models (user's last picks) shown at top of the list
  const recentModels = useMemo(() => {
    const byId = new Map(models.map((m) => [m.id, m]));
    return recentIds
      .map((id) => byId.get(id))
      .filter((m): m is ModelOption => !!m);
  }, [models, recentIds]);

  // Full list minus recent entries (no duplicates)
  const recentSet = useMemo(
    () => new Set(recentModels.map((m) => m.id)),
    [recentModels],
  );
  const fullProviders = useMemo(
    () =>
      groups.map((g) => ({
        title: g.title,
        items: g.items.filter((m) => !recentSet.has(m.id)),
      })),
    [groups, recentSet],
  );

  // All options flattened for keyboard navigation
  const allOptions = useMemo(
    () => [...recentModels, ...fullProviders.flatMap((g) => g.items)],
    [recentModels, fullProviders],
  );

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setFocusIdx(-1);
      }
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);

  const recordRecent = useCallback((id: string) => {
    setRecentIds((prev) => {
      const next = [id, ...prev.filter((x) => x !== id)].slice(0, RECENT_LIMIT);
      writeRecentModels(next);
      return next;
    });
  }, []);

  // Keyboard navigation + Escape close
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'Escape':
          setOpen(false);
          setFocusIdx(-1);
          break;
        case 'ArrowDown':
          e.preventDefault();
          setFocusIdx((i) => Math.min(i + 1, allOptions.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setFocusIdx((i) => Math.max(i - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (focusIdx >= 0 && focusIdx < allOptions.length) {
            recordRecent(allOptions[focusIdx].id);
            onChange(allOptions[focusIdx].id);
            setOpen(false);
            setFocusIdx(-1);
          }
          break;
      }
    };
    document.addEventListener('keydown', h);
    return () => document.removeEventListener('keydown', h);
  }, [open, focusIdx, allOptions, onChange, recordRecent]);

  // Scroll focused item into view
  useEffect(() => {
    if (!open || focusIdx < 0 || !listRef.current) return;
    const items = listRef.current.querySelectorAll('[data-model-option]');
    items[focusIdx]?.scrollIntoView({ block: 'nearest' });
  }, [open, focusIdx]);

  const handleSelect = useCallback(
    (id: string) => {
      onChange(id);
      recordRecent(id);
      setOpen(false);
      setFocusIdx(-1);
    },
    [onChange, recordRecent],
  );

  return (
    <div className="relative inline-flex items-center" ref={ref}>
      <button
        className={`inline-flex items-center gap-1 px-2 h-[26px] min-w-[140px] border rounded-md bg-transparent text-xs font-[inherit] cursor-pointer transition-all duration-150 max-w-[180px] border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-border)] hover:text-[var(--color-text-primary)] ${!hasLoadedOnce || isEmpty || !current ? 'justify-center' : ''}`}
        onClick={() => {
          if (isEmpty) {
            onConfigure?.();
          } else {
            setOpen(!open);
            setFocusIdx(-1);
          }
        }}
        type="button"
        title={isEmpty ? t('model.configure') : current?.label}
        aria-expanded={isEmpty ? undefined : open}
        aria-haspopup={isEmpty ? undefined : 'listbox'}
      >
        <span className="overflow-hidden text-ellipsis whitespace-nowrap">
          <SelectorLabel
            hasLoadedOnce={hasLoadedOnce}
            isEmpty={isEmpty}
            current={current}
          />
        </span>
        {hasLoadedOnce && current && (
          <ChevronDown
            size={10}
            className={`flex-shrink-0 text-[var(--color-text-muted)] transition-transform duration-150 ease ${open ? 'rotate-180' : ''}`}
          />
        )}
      </button>

      {open && !isEmpty && (
        <div
          className="absolute bottom-[calc(100%+8px)] left-0 min-w-[200px] max-h-[280px] overflow-y-auto bg-[var(--color-surface-raised)] rounded-[10px] shadow-[0_12px_40px_rgba(0,0,0,0.25)] z-[500] p-1"
          ref={listRef}
          role="listbox"
        >
          <OptionsList
            providers={fullProviders}
            recentModels={recentModels}
            selectedModel={selectedModel}
            focusIdx={focusIdx}
            onSelect={handleSelect}
          />
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              onConfigure?.();
            }}
            className="w-full px-3 py-2 mt-1 text-left text-xs text-[var(--color-text-muted)] border-t border-[var(--color-border)] bg-transparent cursor-pointer transition-colors hover:text-[var(--color-text-primary)]"
          >
            {t('model.manageKeys')}
          </button>
        </div>
      )}
    </div>
  );
}
