import { useState } from 'react';
import { Play, X } from 'lucide-react';
import type { PromptItem } from '../../api/client/prompts';
import { MonoBadge, StatusBadge } from './PromptBadges';

interface Props {
  prompt: PromptItem;
  onClose: () => void;
}

export default function PromptDetailDrawer({ prompt, onClose }: Props) {
  const [testInput, setTestInput] = useState('');
  return (
    <>
      <div
        className="fixed inset-0 bg-[var(--color-overlay)] backdrop-blur-sm z-40"
        onClick={onClose}
      />
      <div className="fixed top-0 right-0 w-[520px] max-w-[92vw] h-full bg-[var(--color-surface-overlay)] border-l border-[var(--color-border)] z-40 flex flex-col shadow-[-12px_0_48px_rgba(0,0,0,0.4)]">
        <div className="flex items-center justify-between px-5 py-[18px] border-b border-[var(--color-border)] shrink-0">
          <span className="text-[15px] font-semibold tracking-[-0.02em] text-[var(--color-text-primary)] truncate pr-3">
            {prompt.name}
          </span>
          <button
            onClick={onClose}
            aria-label="关闭"
            className="w-7 h-7 rounded-md border-none bg-transparent text-[var(--color-text-muted)] cursor-pointer inline-flex items-center justify-center hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
          >
            <X size={14} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          <Section label="基本信息">
            <KVRow label="名称" value={prompt.name} />
            <KVRow label="描述" value={prompt.description || '—'} />
            <KVRow
              label="状态"
              value={<StatusBadge status={prompt.status} />}
            />
            <KVRow
              label="版本"
              value={<MonoBadge>{prompt.version}</MonoBadge>}
            />
            <KVRow
              label="调用次数"
              value={
                <span className="font-mono text-[var(--color-accent)]">
                  {(
                    (prompt as unknown as { uses?: number }).uses ?? 0
                  ).toLocaleString()}
                </span>
              }
            />
            <KVRow
              label="更新时间"
              value={new Date(prompt.created_at).toLocaleString('zh-CN')}
            />
            <KVRow label="类别" value={prompt.category} />
          </Section>

          <Section label="提示词内容">
            <pre className="m-0 p-3.5 rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] text-[12px] font-mono leading-[1.7] text-[var(--color-text-secondary)] whitespace-pre-wrap overflow-x-auto">
              {prompt.content ||
                `你是一位专业的${prompt.name}助手。\n请根据提供的知识库内容，准确回答用户的问题。\n\n{{context}}\n\n用户问题：{{question}}\n\n请用清晰、简洁的语言回答。`}
            </pre>
          </Section>

          <Section label="测试运行">
            <textarea
              value={testInput}
              onChange={(e) => setTestInput(e.target.value)}
              placeholder="输入测试问题…"
              rows={3}
              className="w-full p-3 rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] text-[13px] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] outline-none focus:border-[color-mix(in_srgb,var(--color-accent)_40%,transparent)] resize-y mb-2.5"
            />
            <button
              disabled={!testInput.trim()}
              className="w-full h-9 rounded-[9px] border-none bg-[var(--color-accent)] text-white text-[13px] font-medium cursor-pointer inline-flex items-center justify-center gap-1.5 disabled:opacity-60 disabled:cursor-not-allowed hover:opacity-90"
            >
              <Play size={12} />
              运行测试
            </button>
          </Section>
        </div>
      </div>
    </>
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
    <div className="grid grid-cols-[100px_1fr] items-center min-h-7 mb-2.5">
      <span className="text-xs text-[var(--color-text-tertiary)]">{label}</span>
      <span className="text-[13px] text-[var(--color-text-primary)]">
        {value}
      </span>
    </div>
  );
}
