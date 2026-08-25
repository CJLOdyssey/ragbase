import { useEffect, useState } from 'react';
import { Modal as AntdModal } from 'antd';
import { useTranslation } from 'react-i18next';
import type { PromptItem } from '../../api/client/prompts';
import { StatusBadge } from './PromptBadges';
import { useToast } from '../../utils/useToast';

interface Props {
  prompt: PromptItem;
  onClose: () => void;
}

/** 只读详情弹窗：数据由父级从缓存派生传入，自身不持有任何行快照。
 *  无 footer——只读视图无可取消/确认动作，右上 ✕ 即关闭；
 *  编辑入口在列表行操作区（PromptTable/PromptGrid）。 */
export default function PromptDetailModal({ prompt, onClose }: Props) {
  const { t } = useTranslation();
  const { toast } = useToast();
  const [copied, setCopied] = useState(false);

  const content = prompt.content?.trim() ? prompt.content : '';
  const uses = (
    (prompt as unknown as { uses?: number }).uses ?? 0
  ).toLocaleString();

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 1600);
    return () => window.clearTimeout(timer);
  }, [copied]);

  const handleCopy = async () => {
    if (!content) return;
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
    } catch {
      toast(t('toast.error'), 'error');
    }
  };

  return (
    <AntdModal
      title={
        <span className="flex items-center gap-2.5 min-w-0 pr-4">
          <span className="text-lg font-semibold text-[var(--color-text-primary)] truncate">
            {prompt.name}
          </span>
          <span className="shrink-0 flex items-center gap-1.5">
            <StatusBadge status={prompt.status} />
            <span className="text-xs font-mono text-[var(--color-text-tertiary)]">
              {prompt.version}
            </span>
          </span>
        </span>
      }
      open={true}
      onCancel={onClose}
      centered
      width={680}
      aria-label={prompt.name}
      footer={null}
    >
      <div className="p-6">
        <Section label={t('prompts.detail.basicInfo')}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2.5">
            <KVRow label={t('prompts.editor.name')} value={prompt.name} />
            <KVRow
              label={t('prompts.editor.description')}
              value={prompt.description || '—'}
            />
            <KVRow label={t('prompts.detail.uses')} value={uses} />
            <KVRow
              label={t('prompts.editor.updatedAt')}
              value={new Date(prompt.created_at).toLocaleString('zh-CN')}
            />
          </div>
        </Section>

        <div className="mb-0">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10.5px] font-mono font-semibold tracking-[0.08em] uppercase text-[var(--color-text-tertiary)]">
              {t('prompts.detail.content')}
            </span>
            <button
              type="button"
              onClick={handleCopy}
              disabled={!content}
              className="inline-flex items-center gap-1 h-7 px-2.5 rounded-md border border-[var(--color-border)] bg-transparent text-[11px] text-[var(--color-text-secondary)] cursor-pointer transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {copied ? t('prompts.detail.copied') : t('prompts.detail.copy')}
            </button>
          </div>
          <pre className="m-0 p-3.5 max-h-[320px] overflow-y-auto rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] text-[12px] font-mono leading-[1.7] text-[var(--color-text-secondary)] whitespace-pre-wrap break-words">
            {content || (
              <span className="text-[var(--color-text-muted)] italic">
                {t('prompts.detail.emptyContent')}
              </span>
            )}
          </pre>
        </div>
      </div>
    </AntdModal>
  );
}

function Section({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-[22px]">
      <div className="text-[10.5px] font-mono font-semibold tracking-[0.08em] uppercase text-[var(--color-text-tertiary)] mb-3">
        {label}
      </div>
      {children}
    </div>
  );
}

function KVRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[88px_1fr] items-center min-h-7 gap-x-2">
      <span className="text-xs text-[var(--color-text-tertiary)]">{label}</span>
      <span className="text-[13px] text-[var(--color-text-primary)] truncate">
        {value}
      </span>
    </div>
  );
}
