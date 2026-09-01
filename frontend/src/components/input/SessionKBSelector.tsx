import { useCallback, useEffect, useRef, useState } from 'react';
import { BookOpen, Check, ChevronDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { listKnowledgeBases } from '../../api/client/knowledgeBases';
import { updateSessionKBs } from '../../api/client/sessions';
import type { KnowledgeBase } from '../../api/client/knowledgeBases';

interface Props {
  sessionId: string | null;
  knowledgeBaseIds: string[];
  onChange: (ids: string[]) => void;
}

export default function SessionKBSelector({
  sessionId,
  knowledgeBaseIds,
  onChange,
}: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [loaded, setLoaded] = useState(false);
  const fetchedRef = useRef(false);
  const ref = useRef<HTMLDivElement>(null);

  const selectedCount = knowledgeBaseIds.length;

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    listKnowledgeBases()
      .then((data) => { setKbs(data); setLoaded(true); })
      .catch(() => { setLoaded(true); });
  }, []);

  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);

  const toggle = useCallback(
    async (kbId: string) => {
      const next = knowledgeBaseIds.includes(kbId)
        ? knowledgeBaseIds.filter((id) => id !== kbId)
        : [...knowledgeBaseIds, kbId];
      onChange(next);
      if (sessionId) {
        try {
          await updateSessionKBs(sessionId, next);
        } catch {
          onChange(knowledgeBaseIds);
        }
      }
    },
    [knowledgeBaseIds, sessionId, onChange],
  );

  if (!sessionId) return null;

  return (
    <div className="relative inline-flex items-center" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="inline-flex items-center justify-center gap-1 px-2 h-[26px] min-w-[60px] border rounded-md bg-transparent text-xs font-[inherit] cursor-pointer transition-all duration-150 border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-border)] hover:text-[var(--color-text-primary)]"
        title={t('kb.chatSelector', '知识库')}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <BookOpen size={12} className="flex-shrink-0" />
        {selectedCount > 0 && (
          <span className="overflow-hidden text-ellipsis whitespace-nowrap">
            {selectedCount}
          </span>
        )}
        <ChevronDown
          size={10}
          className={`flex-shrink-0 text-[var(--color-text-muted)] transition-transform duration-150 ease ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div
          className="absolute bottom-[calc(100%+8px)] left-0 min-w-[220px] max-h-[280px] overflow-y-auto bg-[var(--color-surface-raised)] rounded-[10px] shadow-[0_12px_40px_rgba(0,0,0,0.25)] z-[500] p-1"
          role="listbox"
          aria-multiselectable
        >
          {!loaded ? (
            <div className="px-3 py-2 text-xs text-[var(--color-text-muted)] text-center">
              {t('common.loading')}
            </div>
          ) : kbs.length === 0 ? (
            <div className="px-3 py-2 text-xs text-[var(--color-text-muted)] text-center">
              {t('kb.noKnowledgeBases', '暂无知识库')}
            </div>
          ) : (
            kbs.map((kb) => {
              const selected = knowledgeBaseIds.includes(kb.id);
              return (
                <button
                  key={kb.id}
                  type="button"
                  onClick={() => toggle(kb.id)}
                  className={`flex items-center gap-2 w-full px-3 py-2 border-none rounded-md bg-transparent text-[var(--color-text-primary)] text-sm cursor-pointer transition-colors duration-100 text-left hover:bg-[var(--color-surface-hover)] ${selected ? 'bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)]' : ''}`}
                  role="option"
                  aria-selected={selected}
                >
                  <Check
                    size={12}
                    className={`flex-shrink-0 ${selected ? 'text-[var(--color-accent)]' : 'text-transparent'}`}
                  />
                  <span className="overflow-hidden text-ellipsis whitespace-nowrap">
                    {kb.name}
                  </span>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
