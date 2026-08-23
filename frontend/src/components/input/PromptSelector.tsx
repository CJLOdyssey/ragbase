import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { listPrompts } from '../../api/client/prompts';
import {
  readSelectedPromptId,
  writeSelectedPromptId,
} from '../../stores/selectedPrompt';

/** 与后端 load_active_user_prompt 门禁一致的状态白名单。 */
const ACTIVE_STATUSES = new Set(['active', 'published', 'enabled']);

interface Option {
  id: string | null;
  label: string;
}

/**
 * 聊天人设提示词选择器 — 仅列出「启用」状态的提示词；草稿不参与对话。
 * 选择结果写入 localStorage（见 stores/selectedPrompt），发送时由
 * chatActions 随 /runs 请求携带 prompt_id。
 */
export default function PromptSelector() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [focusIdx, setFocusIdx] = useState(-1);
  const [selectedId, setSelectedId] = useState<string | null>(
    readSelectedPromptId() ?? null,
  );
  const ref = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const promptsQuery = useQuery({
    queryKey: ['prompts'],
    queryFn: listPrompts,
    staleTime: 30_000,
  });

  const actives = useMemo(
    () => (promptsQuery.data ?? []).filter((p) => ACTIVE_STATUSES.has(p.status)),
    [promptsQuery.data],
  );

  // 所选提示词被停用/删除 → 视图回落为「不使用」（发送路径由后端 active 门禁兜底）
  const effectiveId = actives.some((p) => p.id === selectedId)
    ? selectedId
    : null;
  const current = actives.find((p) => p.id === effectiveId);

  const options = useMemo<Option[]>(
    () => [
      { id: null, label: t('promptSelect.none') },
      ...actives.map((p) => ({ id: p.id, label: p.name })),
    ],
    [actives, t],
  );

  const close = () => {
    setOpen(false);
    setFocusIdx(-1);
  };

  const handleSelect = (opt: Option) => {
    writeSelectedPromptId(opt.id);
    setSelectedId(opt.id);
    close();
  };

  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) close();
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'Escape':
          close();
          break;
        case 'ArrowDown':
          e.preventDefault();
          setFocusIdx((i) => Math.min(i + 1, options.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setFocusIdx((i) => Math.max(i - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (focusIdx >= 0 && focusIdx < options.length) {
            handleSelect(options[focusIdx]);
          }
          break;
      }
    };
    document.addEventListener('keydown', h);
    return () => document.removeEventListener('keydown', h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, focusIdx, options]);

  useEffect(() => {
    if (!open || focusIdx < 0 || !listRef.current) return;
    const items = listRef.current.querySelectorAll('[data-prompt-option]');
    items[focusIdx]?.scrollIntoView({ block: 'nearest' });
  }, [open, focusIdx]);

  return (
    <div className="relative inline-flex items-center" ref={ref}>
      <button
        type="button"
        onClick={() => {
          setFocusIdx(-1);
          setOpen(!open);
        }}
        title={current?.name ?? t('promptSelect.label')}
        aria-expanded={open}
        aria-haspopup="listbox"
        className={`inline-flex items-center gap-1 px-2 h-[26px] min-w-[96px] max-w-[160px] border rounded-md bg-transparent text-xs font-[inherit] cursor-pointer transition-all duration-150 border-[var(--color-border)] ${
          current
            ? 'text-[var(--color-accent)]'
            : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
        }`}
      >
        <FileText size={12} className="flex-shrink-0" />
        <span className="overflow-hidden text-ellipsis whitespace-nowrap">
          {current?.name ?? t('promptSelect.label')}
        </span>
        <ChevronDown
          size={10}
          className={`flex-shrink-0 text-[var(--color-text-muted)] transition-transform duration-150 ease ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div
          className="absolute bottom-[calc(100%+8px)] left-0 min-w-[200px] max-h-[280px] overflow-y-auto bg-[var(--color-surface-raised)] rounded-[10px] shadow-[0_12px_40px_rgba(0,0,0,0.25)] z-[500] p-1"
          ref={listRef}
          role="listbox"
          aria-label={t('promptSelect.label')}
        >
          {options.map((opt, idx) =>
            opt.id === null ? (
              <button
                key="__none"
                type="button"
                role="option"
                aria-selected={!effectiveId}
                data-prompt-option
                onClick={() => handleSelect(opt)}
                className={`w-full px-3 py-2 text-left text-xs rounded-md border-none bg-transparent cursor-pointer transition-colors duration-100 border-b border-[var(--color-border-subtle)] mb-1 ${
                  !effectiveId
                    ? 'text-[var(--color-accent)] bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)]'
                    : 'text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]'
                } ${idx === focusIdx ? 'outline-2 outline-[var(--color-accent)] outline-offset-[-2px]' : ''}`}
              >
                {opt.label}
              </button>
            ) : (
              <button
                key={opt.id}
                type="button"
                role="option"
                aria-selected={opt.id === effectiveId}
                data-prompt-option
                title={opt.label}
                onClick={() => handleSelect(opt)}
                className={`flex items-center justify-between w-full px-3 py-2 border-none rounded-md bg-transparent text-sm cursor-pointer transition-colors duration-100 text-left hover:bg-[var(--color-surface-hover)] ${
                  opt.id === effectiveId
                    ? 'bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)] text-[var(--color-accent)]'
                    : 'text-[var(--color-text-primary)]'
                } ${idx === focusIdx ? 'outline-2 outline-[var(--color-accent)] outline-offset-[-2px]' : ''}`}
              >
                <span className="overflow-hidden text-ellipsis whitespace-nowrap">
                  {opt.label}
                </span>
                <span className="flex-shrink-0 ml-2 text-[10px] font-mono text-[var(--color-text-tertiary)]">
                  {actives.find((p) => p.id === opt.id)?.version}
                </span>
              </button>
            ),
          )}
          {actives.length === 0 && (
            <div className="px-3 py-2.5 text-xs text-[var(--color-text-muted)]">
              {t('promptSelect.empty')}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
