import {
  groupThinkingNodes,
  markdownComponents,
  ThinkingMarkdown,
  ThinkingNodeItem,
} from '../thinking';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

const t = (k: string) => k;

describe('groupThinkingNodes', () => {
  it('parses plain text into a single node', () => {
    const items = groupThinkingNodes('just some text');
    expect(items).toHaveLength(1);
    expect(items[0]).toMatchObject({ type: 'node', parsed: null });
  });

  it('pairs [tools] call with following [result]', () => {
    const items = groupThinkingNodes('[tools] python\n\n[result] done');
    expect(items).toHaveLength(1);
    expect(items[0].type).toBe('toolPair');
    if (items[0].type === 'toolPair') {
      expect(items[0].callParsed.prefix).toBe('tools');
      expect(items[0].resultParsed.prefix).toBe('result');
      expect(items[0].resultNode).toContain('done');
    }
  });

  it('synthesizes an empty result for a lone [tools] node', () => {
    const items = groupThinkingNodes('[tools] search_db');
    expect(items).toHaveLength(1);
    expect(items[0].type).toBe('toolPair');
    if (items[0].type === 'toolPair') {
      expect(items[0].resultNode).toBe('[result] search_db');
    }
  });

  it('handles emoji-prefixed nodes (🔧/📡/📋)', () => {
    const items = groupThinkingNodes(
      '🔧 run script\n\n📡 read sensor\n\n📋 note',
    );
    expect(items).toHaveLength(3);
    expect(items[0]).toMatchObject({ type: 'toolPair' });
    if (items[0].type === 'toolPair') {
      expect(items[0].callParsed.prefix).toBe('tools');
    }
    expect(items[2]).toMatchObject({
      type: 'node',
      parsed: { prefix: 'info' },
    });
  });

  it('keeps [info] nodes as plain nodes with parsed prefix', () => {
    const items = groupThinkingNodes('[info] nothing to worry');
    expect(items).toHaveLength(1);
    expect(items[0]).toMatchObject({
      type: 'node',
      parsed: { prefix: 'info' },
    });
  });

  it('splits multiple tool calls separated by blank lines', () => {
    const items = groupThinkingNodes(
      '[tools] a\n\n[result] 1\n\n[tools] b\n\n[result] 2',
    );
    expect(items).toHaveLength(2);
    expect(items.every((i) => i.type === 'toolPair')).toBe(true);
  });
});

describe('markdownComponents / ThinkingMarkdown', () => {
  it('renders markdown with linkified bare http urls', () => {
    render(
      <ThinkingMarkdown t={t}>see https://example.com link</ThinkingMarkdown>,
    );
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', 'https://example.com');
  });

  it('renders markdown with linkified /api/attachments/ urls', () => {
    render(<ThinkingMarkdown t={t}>{'/api/attachments/42'}</ThinkingMarkdown>);
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/api/attachments/42');
  });

  it('keeps plain text without urls unlinked', () => {
    render(<ThinkingMarkdown t={t}>just plain text</ThinkingMarkdown>);
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getByText('just plain text')).toBeInTheDocument();
  });

  it('renders inline code via CodeBlock', () => {
    render(<ThinkingMarkdown t={t}>{'`const a = 1`'}</ThinkingMarkdown>);
    expect(screen.getByText('const a = 1')).toBeInTheDocument();
  });

  it('exposes a code component from markdownComponents', () => {
    const comps = markdownComponents(t);
    expect(comps.code).toBeTypeOf('function');
    expect(comps.p).toBeTypeOf('function');
    expect(comps.ul).toBeTypeOf('function');
  });
});

describe('ThinkingNodeItem', () => {
  it('renders a toolPair item expandable to reveal result', () => {
    const item = {
      type: 'toolPair' as const,
      callNode: '[tools] python',
      resultNode: '[result] ok',
      callParsed: { prefix: 'tools', rest: 'python' },
      resultParsed: { prefix: 'result', rest: 'ok' },
    };
    render(<ThinkingNodeItem item={item} t={t} />);
    expect(screen.getByText(/\[tools\]/)).toBeInTheDocument();
    // initially collapsed — no result text
    expect(screen.queryByText('ok')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('ok')).toBeInTheDocument();
  });

  it('renders a plain node with info prefix badge', () => {
    const item = {
      type: 'node' as const,
      node: '[info] hello',
      parsed: { prefix: 'info', rest: 'hello' },
    };
    render(<ThinkingNodeItem item={item} t={t} />);
    expect(screen.getByText('[info]')).toBeInTheDocument();
    expect(screen.getByText('hello')).toBeInTheDocument();
  });

  it('renders unparsed text trimmed', () => {
    const item = {
      type: 'node' as const,
      node: '  raw line  ',
      parsed: null,
    };
    render(<ThinkingNodeItem item={item} t={t} />);
    expect(screen.getByText('raw line')).toBeInTheDocument();
  });
});
