import type { ReactNode } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { CopyBtn } from './CopyBtn';

export function CodeBlock({
  className,
  children,
  t,
}: {
  className?: string;
  children: ReactNode;
  t: (key: string) => string;
}) {
  const match = /language-(\w+)/.exec(className || '');
  const codeString = String(children).replace(/\n$/, '');
  if (match) {
    return (
      <div className="my-3 rounded-lg overflow-hidden bg-[var(--color-surface-elevated)]">
        <div className="flex items-center justify-between px-3 py-2 bg-[var(--color-surface-raised)]">
          <span className="text-xs text-[var(--color-text-muted)] font-[var(--font-mono)]">
            {match[1]}
          </span>
          <CopyBtn
            text={codeString}
            label={t('teamMessage.copy')}
            className="flex items-center gap-1 px-2 py-1 bg-transparent border-none rounded text-[var(--color-text-muted)] cursor-pointer text-xs transition-all duration-150 hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
          />
        </div>
        <SyntaxHighlighter
          style={oneDark}
          language={match[1]}
          PreTag="div"
          customStyle={{
            margin: 0,
            borderRadius: '0 0 var(--radius-btn) var(--radius-btn)',
          }}
        >
          {codeString}
        </SyntaxHighlighter>
      </div>
    );
  }
  return (
    <code className="bg-[color-mix(in_srgb,var(--color-accent-soft)_15%,transparent)] text-[var(--color-accent-soft)] px-1.5 py-0.5 rounded text-[0.9em] font-[var(--font-mono)]">
      {children}
    </code>
  );
}
