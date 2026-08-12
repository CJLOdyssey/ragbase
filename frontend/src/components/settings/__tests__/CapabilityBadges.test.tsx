import CapabilityBadges from '../CapabilityBadges';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

describe('CapabilityBadges', { tags: ['unit'] }, () => {
  it('renders an em dash for empty capabilities', () => {
    render(<CapabilityBadges capabilities={[]} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('maps known capabilities to badge translation keys', () => {
    render(<CapabilityBadges capabilities={['llm', 'embedding']} />);
    expect(screen.getByText('providerEdit.badge.llm')).toBeInTheDocument();
    expect(
      screen.getByText('providerEdit.badge.embedding'),
    ).toBeInTheDocument();
  });

  it('falls back to the raw capability for unknown keys', () => {
    render(<CapabilityBadges capabilities={['custom-x']} />);
    expect(screen.getByText('custom-x')).toBeInTheDocument();
  });
});
