import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CodeBlock } from '@/components/AgentStudio/messages/CodeBlock';

vi.mock('react-syntax-highlighter', () => ({
  Prism: ({ children }: { children: string }) => <pre data-testid="syntax">{children}</pre>,
}));
vi.mock('react-syntax-highlighter/dist/esm/styles/prism', () => ({ oneDark: {} }));

const t = (key: string) => key;

describe('CodeBlock', { tags: ['unit'] }, () => {
  it('renders inline code when no language class', () => {
    render(<CodeBlock t={t}>hello</CodeBlock>);
    expect(screen.getByText('hello').tagName).toBe('CODE');
  });

  it('renders syntax-highlighted block with language', () => {
    render(<CodeBlock className="language-js" t={t}>const x = 1;</CodeBlock>);
    expect(screen.getByText('js')).toBeInTheDocument();
    expect(screen.getByTestId('syntax')).toBeInTheDocument();
  });
});
