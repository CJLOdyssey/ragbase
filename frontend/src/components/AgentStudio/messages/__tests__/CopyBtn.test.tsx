import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('@/hooks/useCopyToClipboard', () => ({
  useCopyToClipboard: () => ({
    copy: vi.fn(),
    isCopied: vi.fn(() => false),
  }),
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

import { CopyBtn } from '@/components/AgentStudio/messages/CopyBtn';

describe('CopyBtn', { tags: ['unit'] }, () => {
  it('renders copy button with label', () => {
    render(<CopyBtn text="hello" label="Copy code" />);
    expect(screen.getByTitle('Copy code')).toBeInTheDocument();
  });

  it('renders with custom className', () => {
    const { container } = render(<CopyBtn text="test" className="custom-class" />);
    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });

  it('calls copy on click', () => {
    render(<CopyBtn text="hello" label="Copy" />);
    fireEvent.click(screen.getByTitle('Copy'));
    expect(screen.getByTitle('Copy')).toBeInTheDocument();
  });
});
