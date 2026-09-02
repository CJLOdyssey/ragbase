import { useCopyToClipboard } from '../../../hooks/useCopyToClipboard';
import { useToast } from '../../../utils/useToast';
import { Check, Copy } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export function CopyBtn({
  text,
  label,
  className,
}: {
  text: string;
  label?: string;
  className?: string;
}) {
  const { copy, isCopied } = useCopyToClipboard();
  const { t } = useTranslation();
  const { toast } = useToast();
  const key = text.slice(0, 32);
  const copied = isCopied(key);
  return (
    <button
      className={`${className || 'min-w-[32px] min-h-[32px] px-1.5 py-1 bg-transparent border-none rounded text-[var(--color-text-muted)] cursor-pointer flex items-center justify-center transition-colors duration-150 hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]'}${copied ? ' !text-[var(--color-accent)] hover:!text-[var(--color-accent)] hover:!bg-[var(--color-surface-hover)]' : ''}`}
      onClick={async () => {
        const ok = await copy(text, key);
        // 复制失败不静默：execCommand/权限拒绝等路径给出可见反馈。
        if (!ok) toast(t('teamMessage.copyFailed'), 'error');
      }}
      title={copied ? t('teamMessage.copied') : label}
      aria-label={copied ? t('teamMessage.copied') : label}
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
    </button>
  );
}
