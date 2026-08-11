import KeyTablePagination from '../KeyTablePagination';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string, opts?: { count?: number }) =>
      opts && typeof opts.count === 'number' ? `共 ${opts.count} 条` : k,
  }),
}));

describe('KeyTablePagination', () => {
  it('renders total count', () => {
    render(
      <KeyTablePagination
        total={100}
        current={1}
        pageSize={10}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByText('共 100 条')).toBeInTheDocument();
  });

  it('returns null when total is zero', () => {
    const { container } = render(
      <KeyTablePagination
        total={0}
        current={1}
        pageSize={10}
        onChange={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders on different current page', () => {
    render(
      <KeyTablePagination
        total={50}
        current={2}
        pageSize={10}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByText('共 50 条')).toBeInTheDocument();
  });
});
