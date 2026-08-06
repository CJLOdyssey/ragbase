import LoadingSkeleton from '../LoadingSkeleton';
import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

describe('LoadingSkeleton', { tags: ['unit'] }, () => {
  it('renders table rows', () => {
    const { container } = render(<LoadingSkeleton rows={3} />);
    expect(container.querySelectorAll('.animate-pulse')).toHaveLength(3);
  });

  it('renders card layout when type is card', () => {
    const { container } = render(<LoadingSkeleton type="card" rows={2} />);
    expect(container.querySelectorAll('.animate-pulse')).toHaveLength(2);
    expect(container.querySelectorAll('[class*="radius-card"]')).toHaveLength(
      2,
    );
  });
});
