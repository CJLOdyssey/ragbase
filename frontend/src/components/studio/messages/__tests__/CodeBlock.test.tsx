import { CodeBlock } from '../CodeBlock';
import { CopyBtn } from '../CopyBtn';
import LazyCodeBlock from '../LazyCodeBlock';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-syntax-highlighter/dist/esm/styles/prism', () => ({
  oneDark: {},
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string) => k,
    i18n: { language: 'zh-CN' },
  }),
}));

const t = (k: string) => k;

describe('CodeBlock', () => {
  it('renders language header when className has language', () => {
    const { container } = render(
      <CodeBlock className="language-ts" t={t}>
        {'const x = 1;\n'}
      </CodeBlock>,
    );
    expect(screen.getByText('ts')).toBeInTheDocument();
    expect(container.querySelector('div')).toBeTruthy();
  });

  it('renders inline code without language', () => {
    const { container } = render(<CodeBlock t={t}>{'const x = 1;'}</CodeBlock>);
    expect(container.querySelector('code')).toHaveTextContent('const x = 1;');
    expect(screen.queryByText('ts')).not.toBeInTheDocument();
  });
});

describe('CopyBtn', () => {
  it('copies text to clipboard and shows copied state', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });
    render(<CopyBtn text="secret" label="teamMessage.copy" />);
    fireEvent.click(screen.getByRole('button', { name: 'teamMessage.copy' }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith('secret'));
    expect(
      screen.getByRole('button', { name: 'teamMessage.copied' }),
    ).toBeInTheDocument();
  });
});

describe('LazyCodeBlock', () => {
  it('renders children via Suspense fallback or loaded block', () => {
    render(<LazyCodeBlock t={t}>{'hello code'}</LazyCodeBlock>);
    expect(screen.getByText('hello code')).toBeInTheDocument();
  });
});
