import { useState } from 'react';
import type * as React from 'react';
import type { ElementContent, Root } from 'hast';
import ReactMarkdown, { type Components } from 'react-markdown';
import { visit } from 'unist-util-visit';
import { CodeBlock } from './messages';

function linkify(text: string): React.ReactNode {
  const parts = text.split(/(https?:\/\/[^\s"',)\]}]+)/g);
  if (parts.length === 1) return text;
  return parts.map((part, i) =>
    /^https?:\/\//.test(part) ? (
      <a
        key={i}
        href={part}
        target="_blank"
        rel="noopener noreferrer"
        className="underline text-[var(--color-accent)] hover:opacity-80 break-all"
      >
        {part}
      </a>
    ) : (
      part
    ),
  );
}

export function markdownComponents(t: (key: string) => string): Components {
  return {
    ul({ children, ...props }) {
      return (
        <ul className="my-2 pl-6 list-outside" {...props}>
          {children}
        </ul>
      );
    },
    ol({ children, ...props }) {
      return (
        <ol className="my-2 pl-6 list-outside list-decimal" {...props}>
          {children}
        </ol>
      );
    },
    li({ children, ...props }) {
      return (
        <li className="my-1 pl-1" {...props}>
          {children}
        </li>
      );
    },
    p({ children, ...props }) {
      return (
        <p className="m-0 mb-3 last:mb-0" {...props}>
          {children}
        </p>
      );
    },
    code({ className, children }) {
      return <CodeBlock className={className} children={children} t={t} />;
    },
    img({ src, alt }) {
      return (
        <img
          src={src}
          alt={alt}
          className="max-w-full h-auto rounded-lg border border-[var(--color-border)]"
        />
      );
    },
  };
}

export function ThinkingMarkdown({
  t,
  children,
}: {
  t: (key: string) => string;
  children: string;
}) {
  return (
    <ReactMarkdown
      rehypePlugins={[rehypeLinkify]}
      components={{
        ...markdownComponents(t),
        p({ children }) {
          return <p className="m-0">{children}</p>;
        },
        a({ href, children }) {
          return (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="underline text-[var(--color-accent)] hover:opacity-80 break-all"
            >
              {children}
            </a>
          );
        },
      }}
    >
      {children}
    </ReactMarkdown>
  );
}

const BARE_URL_RE =
  /(https?:\/\/[^\s"',)\]}]+|\/api\/attachments\/[^\s"',)\]}]+)/g;

export function rehypeLinkify() {
  return (tree: Root) => {
    visit(tree, 'text', (node, index, parent) => {
      if (
        !parent ||
        typeof node.value !== 'string' ||
        typeof index !== 'number'
      )
        return;
      if (parent.type === 'element' && parent.tagName === 'a') return;
      const parts = node.value.split(BARE_URL_RE);
      if (parts.length === 1) return;
      const children: ElementContent[] = [];
      for (const part of parts) {
        if (!part) continue;
        if (/^(https?:\/\/|\/api\/attachments\/)/.test(part)) {
          children.push({
            type: 'element',
            tagName: 'a',
            properties: {
              href: part,
              target: '_blank',
              rel: ['noopener', 'noreferrer'],
            },
            children: [{ type: 'text', value: part }],
          });
        } else {
          children.push({ type: 'text', value: part });
        }
      }
      parent.children.splice(index, 1, ...children);
      return index + children.length - 1;
    });
  };
}

type ParsedNode = { prefix: string; rest: string } | null;

function parseNode(text: string): ParsedNode {
  const t = text.trim();
  const match = t.match(/^\[(tools|mcp|skill|result|info)\]\s+(.*)/);
  if (match) return { prefix: match[1], rest: match[2] };

  if (t.startsWith('🔧'))
    return { prefix: 'tools', rest: t.replace(/^🔧\s*/, '') };
  if (t.startsWith('📡'))
    return { prefix: 'mcp', rest: t.replace(/^📡\s*/, '') };
  if (t.startsWith('🛠️'))
    return { prefix: 'skill', rest: t.replace(/^🛠️\s*/, '') };
  if (t.startsWith('📥'))
    return { prefix: 'result', rest: t.replace(/^📥\s*/, '') };
  if (t.startsWith('📋') || t.startsWith('📏'))
    return { prefix: 'info', rest: t.replace(/^[^\s]+\s*/, '') };

  return null;
}

type ThinkingItem =
  | { type: 'node'; node: string; parsed: ParsedNode }
  | {
      type: 'toolPair';
      callNode: string;
      resultNode: string;
      callParsed: NonNullable<ParsedNode>;
      resultParsed: NonNullable<ParsedNode>;
    };

export function groupThinkingNodes(text: string): ThinkingItem[] {
  const nodes = text
    .split(/\n{2,}|(?=\[(?:tools|mcp|skill|result|info)\]|🔧|📡|🛠️|📋|📥)/)
    .filter(Boolean);
  const items: ThinkingItem[] = [];
  for (let i = 0; i < nodes.length; i++) {
    const cur = parseNode(nodes[i]);
    const isToolCall =
      cur &&
      (cur.prefix === 'tools' ||
        cur.prefix === 'mcp' ||
        cur.prefix === 'skill');
    if (isToolCall && i + 1 < nodes.length) {
      const nxt = parseNode(nodes[i + 1]);
      if (nxt && nxt.prefix === 'result') {
        items.push({
          type: 'toolPair',
          callNode: nodes[i],
          resultNode: nodes[i + 1],
          callParsed: cur,
          resultParsed: nxt,
        });
        i++;
        continue;
      }
    }
    // [tools] without [result] → create toolPair with empty result
    if (isToolCall) {
      items.push({
        type: 'toolPair',
        callNode: nodes[i],
        resultNode: `[result] ${cur.rest}`,
        callParsed: cur,
        resultParsed: { prefix: 'result', rest: cur.rest },
      });
      continue;
    }
    items.push({ type: 'node', node: nodes[i], parsed: cur });
  }
  return items;
}

function ToolCallCard({
  callParsed,
  resultParsed,
  t,
}: {
  callParsed: NonNullable<ParsedNode>;
  resultParsed: NonNullable<ParsedNode>;
  t: (key: string) => string;
}) {
  const [expanded, setExpanded] = useState(false);
  const resultDisplay = resultParsed.rest.replace(/^\w+\s*(?:→|返回:)\s*/, '');

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        className="cursor-pointer select-none rounded-sm hover:bg-[var(--color-surface-hover)] transition-colors duration-150"
        onClick={() => setExpanded(!expanded)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setExpanded(!expanded);
          }
        }}
      >
        <div className="text-base leading-[1.65] text-[var(--color-text-secondary)]">
          <span>[{callParsed.prefix}]</span>{' '}
          <code className="text-[0.85em] font-[var(--font-mono)] break-all">
            {linkify(callParsed.rest)}
          </code>
        </div>
      </div>

      {expanded && (
        <div className="mt-1 flex gap-1.5 text-base leading-[1.65] text-[var(--color-text-muted)]">
          <span className="flex-none select-none text-[var(--color-text-tertiary)]">
            ⟶
          </span>
          <div className="flex-1 min-w-0">
            <ThinkingMarkdown t={t}>{resultDisplay}</ThinkingMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

function ThinkingNodeDot() {
  return (
    <div className="absolute -left-3 top-[6px] w-2 h-2 rounded-full bg-[var(--color-text-muted)] border-2 border-[var(--color-surface)] z-[1]" />
  );
}

export function ThinkingNodeItem({
  item,
  t,
}: {
  item: ThinkingItem;
  t: (key: string) => string;
}) {
  if (item.type === 'toolPair') {
    return (
      <div className="relative mb-2.5 last:mb-0 pl-3">
        <ThinkingNodeDot />
        <ToolCallCard
          callParsed={item.callParsed}
          resultParsed={item.resultParsed}
          t={t}
        />
      </div>
    );
  }

  const parsed = item.parsed;
  const isInfo = parsed?.prefix === 'info';
  const displayText = parsed === null ? item.node.trim() : parsed.rest;
  return (
    <div className="relative mb-2.5 last:mb-0 leading-[1.65] pl-3">
      <ThinkingNodeDot />
      <div className="text-[var(--color-text-muted)]">
        {isInfo && (
          <span className="text-[var(--color-text-tertiary)]">[info] </span>
        )}
        <ThinkingMarkdown t={t}>{displayText}</ThinkingMarkdown>
      </div>
    </div>
  );
}
