import EmptyState from '../shared/EmptyState';
import { History } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { PromptItem } from '../../api/client/prompts';
import type { VersionItem } from '../../api/client/versions';

interface Props {
  prompt: PromptItem;
  versions: VersionItem[];
  onClose: () => void;
  onView: (v: VersionItem) => void;
  onRollback: (v: VersionItem) => void;
}

export default function PromptHistoryModal({
  prompt,
  versions,
  onClose,
  onView,
  onRollback,
}: Props) {
  const { t } = useTranslation();
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-[var(--color-overlay)] backdrop-blur-[6px]"
      onClick={onClose}
    >
      <div
        className="w-full max-w-[640px] max-h-[80vh] rounded-2xl flex flex-col overflow-hidden bg-[var(--color-surface-overlay)] border border-[var(--color-border-strong)] shadow-[var(--shadow-lg)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-[18px] border-b border-[var(--color-border)] shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center border text-[var(--color-accent-soft)] bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)] border-[color-mix(in_srgb,var(--color-accent)_22%,transparent)]">
              <History size={14} />
            </div>
            <div className="flex flex-col">
              <h2 className="m-0 text-[15px] font-semibold tracking-[-0.02em] text-[var(--color-text-primary)]">
                {t('prompts.history.title')}
              </h2>
              <span className="text-[11px] font-mono text-[var(--color-text-tertiary)]">
                {prompt.name}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded-lg border bg-transparent text-[var(--color-text-muted)] text-[12.5px] cursor-pointer border-[var(--color-border)] hover:bg-[var(--color-surface-hover)]"
          >
            {t('common.close')}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {versions.length === 0 ? (
            <div className="py-8 text-center">
              <EmptyState
                icon={<History size={24} />}
                title={t('prompts.history.empty')}
              />
            </div>
          ) : (
            <ul className="flex flex-col gap-2 m-0 p-0 list-none">
              {versions.map((version) => (
                <li
                  key={version.id}
                  className="flex items-center justify-between gap-3 px-4 py-3.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)]"
                >
                  <div className="flex flex-col gap-0.5 flex-1 min-w-0">
                    <span className="text-[13px] font-medium text-[var(--color-text-primary)]">
                      {t('prompts.history.version', {
                        num: version.version_num,
                      })}
                    </span>
                    <span className="text-[11.5px] font-mono text-[var(--color-text-tertiary)]">
                      {new Date(version.created_at).toLocaleString('zh-CN')}
                      {version.created_by
                        ? ` · ${version.created_by.slice(0, 8)}`
                        : ''}
                    </span>
                  </div>
                  <div className="flex gap-1.5 shrink-0">
                    <button
                      onClick={() => onView(version)}
                      className="px-3 py-1.5 rounded-lg border bg-[var(--color-surface)] text-[var(--color-text-muted)] text-[12.5px] cursor-pointer border-[var(--color-border)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
                    >
                      {t('prompts.history.view')}
                    </button>
                    <button
                      onClick={() => onRollback(version)}
                      className="px-3 py-1.5 rounded-lg border-none text-white text-[12.5px] font-medium cursor-pointer bg-[var(--color-accent)] hover:opacity-90"
                    >
                      {t('prompts.version.rollback')}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
