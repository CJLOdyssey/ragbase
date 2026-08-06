import EmptyState from '@/components/shared/EmptyState';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

describe('EmptyState', { tags: ['unit'] }, () => {
  it('renders default icon and title when no props provided', () => {
    render(<EmptyState />);
    expect(screen.getByRole('heading')).toBeInTheDocument();
  });

  it('renders custom icon and title', () => {
    render(
      <EmptyState
        icon={<span data-testid="icon">X</span>}
        title="No items found"
      />,
    );
    expect(screen.getByTestId('icon')).toBeInTheDocument();
    expect(screen.getByText('No items found')).toBeInTheDocument();
  });

  it('renders description when provided', () => {
    render(
      <EmptyState
        icon={<span>X</span>}
        title="Empty"
        description="Nothing here"
      />,
    );
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
  });

  it('does not render description when not provided', () => {
    render(<EmptyState icon={<span>X</span>} title="Empty" />);
    expect(screen.queryByText(/description/)).toBeNull();
  });

  it('renders action when provided', () => {
    render(<EmptyState action={<button>Click me</button>} />);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });
});
