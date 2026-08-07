import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Archive, MoreVertical, Pencil, Plus, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export interface ListItem {
  id: string;
  name: string;
  description?: string;
  enabled: boolean;
  [key: string]: unknown;
}

interface Props<T extends ListItem> {
  title: string;
  items: T[];
  presets: { id: string; name: string; description?: string }[];
  emptyLabel: string;
  hideHeader?: boolean;
  onToggle: (id: string) => void;
  onAdd: () => void;
  onRemove: (id: string) => void;
  onEditFull?: (item: T) => void;
  onArchive?: (item: T) => void;
}

function ItemMenu({
  onEdit,
  onArchive,
  archived,
  onDelete,
}: {
  onEdit?: () => void;
  onArchive?: () => void;
  archived: boolean;
  onDelete?: () => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  useEffect(() => {
    if (!open) return;
    const rect = btnRef.current?.getBoundingClientRect();
    if (rect) setPos({ top: rect.bottom + 4, left: rect.left - 80 });
  }, [open]);

  const close = () => setOpen(false);

  return (
    <>
      <button
        ref={btnRef}
        className="inline-flex items-center justify-center p-1 rounded border-none bg-transparent text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open);
        }}
      >
        <MoreVertical size={14} />
      </button>
      {open &&
        createPortal(
          <>
            <div className="fixed inset-0 z-[99998]" onClick={close} />
            <div
              className="bg-[var(--color-surface-overlay)] border border-[var(--color-border)] rounded-lg p-1 min-w-[140px] shadow-[0_4px_16px_rgba(0,0,0,0.15)] z-[99999]"
              style={{ position: 'fixed', top: pos.top, left: pos.left }}
            >
              {onEdit && (
                <button
                  className="flex items-center gap-2 py-2 px-2.5 rounded-md cursor-pointer transition-colors duration-150 border-none bg-transparent w-full text-sm text-[var(--color-text-secondary)] text-left hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
                  onClick={() => {
                    onEdit();
                    close();
                  }}
                >
                  <Pencil size={14} />
                  <span>{t('workstation.edit')}</span>
                </button>
              )}
              {onArchive && archived ? (
                <span className="flex items-center gap-2 py-2 px-2.5 rounded-md w-full text-sm text-[var(--color-text-muted)] text-left cursor-default">
                  <Archive size={14} />
                  <span>{t('workstation.archived')}</span>
                </span>
              ) : onArchive ? (
                <button
                  className="flex items-center gap-2 py-2 px-2.5 rounded-md cursor-pointer transition-colors duration-150 border-none bg-transparent w-full text-sm text-[var(--color-text-secondary)] text-left hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
                  onClick={() => {
                    onArchive();
                    close();
                  }}
                >
                  <Archive size={14} />
                  <span>{t('workstation.archive')}</span>
                </button>
              ) : null}
              {onDelete && (
                <button
                  className="flex items-center gap-2 py-2 px-2.5 rounded-md cursor-pointer transition-colors duration-150 border-none bg-transparent w-full text-sm text-[var(--color-danger)] text-left hover:bg-[color-mix(in_srgb,var(--color-danger)_10%,transparent)]"
                  onClick={() => {
                    onDelete();
                    close();
                  }}
                >
                  <Trash2 size={14} />
                  <span>{t('workstation.delete')}</span>
                </button>
              )}
            </div>
          </>,
          document.body,
        )}
    </>
  );
}

export default function ConfigItemList<T extends ListItem>({
  title,
  items,
  presets,
  emptyLabel,
  hideHeader = false,
  onToggle,
  onAdd,
  onRemove,
  onEditFull,
  onArchive,
}: Props<T>) {
  const { t } = useTranslation();
  return (
    <div className="agent-config-list flex-1 min-h-0">
      {!hideHeader && (
        <div className="agent-config-list-header">
          <span>
            {title} ({items.length})
          </span>
          <button
            className="inline-flex items-center justify-center gap-2 px-2 py-1 rounded-md text-xs font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
            onClick={onAdd}
          >
            <Plus size={14} /> {t('configItem.add')}
          </button>
        </div>
      )}
      <div className="flex flex-col gap-2">
        {items.map((item) => (
          <div
            key={item.id}
            className={`flex items-center justify-between px-3 py-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-lg transition-[background] duration-150 hover:bg-[var(--color-surface-hover)] ${item.enabled ? '!bg-[color-mix(in_srgb,var(--color-accent)_8%,transparent)] !border-[color-mix(in_srgb,var(--color-accent)_20%,transparent)]' : ''}`}
          >
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={item.enabled}
                onChange={() => onToggle(item.id)}
              />
              <div className="flex flex-col">
                <span className="text-sm font-medium text-[var(--color-text-primary)]">
                  {item.name}
                  {item.is_builtin === true && (
                    <span className="ml-1.5 inline-block py-0.5 px-1.5 rounded text-[10px] font-medium bg-[var(--color-accent)]/10 text-[var(--color-accent)] align-middle">
                      内置
                    </span>
                  )}
                </span>
                {item.description && (
                  <span className="text-xs text-[var(--color-text-muted)]">
                    {item.description}
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <ItemMenu
                onEdit={
                  onEditFull && item.is_builtin !== true
                    ? () => onEditFull(item)
                    : undefined
                }
                onArchive={
                  onArchive && item.is_builtin !== true
                    ? () => onArchive(item)
                    : undefined
                }
                archived={item.archived === true}
                onDelete={
                  item.is_builtin === true ? undefined : () => onRemove(item.id)
                }
              />
            </div>
          </div>
        ))}
        {presets
          .filter((p) => !items.some((i) => i.id === p.id))
          .map((p) => (
            <div
              key={p.id}
              className="flex items-center justify-between px-3 py-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-lg transition-[background] duration-150 hover:bg-[var(--color-surface-hover)]"
            >
              <div className="flex items-center gap-3">
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-[var(--color-text-primary)]">
                    {p.name}
                  </span>
                  {p.description && (
                    <span className="text-xs text-[var(--color-text-muted)]">
                      {p.description}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  className="inline-flex items-center justify-center p-1 rounded border-none bg-transparent text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
                  onClick={() => onToggle(p.id)}
                >
                  <Plus size={14} />
                </button>
              </div>
            </div>
          ))}
        {items.length === 0 && presets.length === 0 && (
          <div className="text-center text-[var(--color-text-muted)] text-sm py-4">
            {emptyLabel}
          </div>
        )}
      </div>
    </div>
  );
}
